import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.services.ingestion import create_document_from_text
from app.services.indexing import index_document
from app.services.qa import qa
from app.services.search import semantic_search

pytestmark = pytest.mark.integration


def test_upload_index_search_qa():
    init_db()
    db: Session = SessionLocal()

    doc, _created = create_document_from_text(
        db,
        filename="e2e.txt",
        content_type="text/plain",
        text="Deterministic chunking keeps boundaries stable. Deduplicate with sha256.",
    )
    assert doc.id is not None

    out = index_document(db, doc.id)
    assert out["chunks_indexed"] >= 1

    s = semantic_search(db, "deduplicate uploads", top_k=5)
    assert "retrieval_ms" in s
    assert len(s["results"]) >= 1

    q = qa(db, "How do we deduplicate documents?", top_k=5)
    assert "answer" in q
    assert "sources" in q
    assert isinstance(q["sources"], list)

    db.close()