from __future__ import annotations

import hashlib
from io import BytesIO

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.db.models import Document, IngestionLog


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_text_from_bytes(data: bytes, content_type: str, filename: str) -> str:
    """
    Required: .txt, .md
    Optional: .pdf via pypdf
    Everything else is treated as utf-8 text (replace errors).
    """
    lower = (filename or "").lower()

    if lower.endswith(".pdf") or content_type == "application/pdf":
        reader = PdfReader(BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()

    return data.decode("utf-8", errors="replace").strip()


def upsert_document_from_bytes(
    db: Session,
    *,
    filename: str,
    content_type: str,
    data: bytes,
) -> tuple[Document, bool]:
    """
    Idempotent upload: deduplicate by sha256.
    Returns (document, created_bool).
    """
    digest = sha256_bytes(data)

    existing = db.query(Document).filter(Document.sha256 == digest).one_or_none()
    if existing:
        db.add(IngestionLog(event="DEDUP", detail=f"sha256={digest} filename={filename}"))
        db.commit()
        return existing, False

    text = extract_text_from_bytes(data, content_type, filename)

    doc = Document(
        filename=filename,
        content_type=content_type,
        sha256=digest,
        extracted_text=text,
    )
    db.add(doc)
    db.flush()

    db.add(IngestionLog(event="INGEST", detail=f"document_id={doc.id} sha256={digest} filename={filename}"))
    db.commit()
    db.refresh(doc)
    return doc, True


def create_document_from_text(
    db: Session,
    *,
    filename: str,
    content_type: str,
    text: str,
) -> tuple[Document, bool]:
    data = text.encode("utf-8")
    return upsert_document_from_bytes(db, filename=filename, content_type=content_type, data=data)