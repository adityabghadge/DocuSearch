from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Document
from app.db.session import get_db
from app.services.ingestion import create_document_from_text, upsert_document_from_bytes

router = APIRouter()


class TextIn(BaseModel):
    filename: str = "text.txt"
    content_type: str = "text/plain"
    text: str


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    doc, created = upsert_document_from_bytes(
        db,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        data=data,
    )
    return {"document_id": doc.id, "created": created, "sha256": doc.sha256}


@router.post("/text")
def upload_text(payload: TextIn, db: Session = Depends(get_db)):
    doc, created = create_document_from_text(
        db,
        filename=payload.filename,
        content_type=payload.content_type,
        text=payload.text,
    )
    return {"document_id": doc.id, "created": created, "sha256": doc.sha256}


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "content_type": d.content_type,
            "sha256": d.sha256,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "sha256": doc.sha256,
        "created_at": doc.created_at,
        "extracted_text_preview": doc.extracted_text[:1200],
    }