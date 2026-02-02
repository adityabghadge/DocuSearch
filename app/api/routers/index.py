from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Document
from app.db.session import get_db
from app.services.indexing import index_document, index_status, reindex_all

router = APIRouter()


@router.post("/reindex")
def reindex(db: Session = Depends(get_db)):
    return reindex_all(db)


@router.post("/{document_id}")
def index_one(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return index_document(db, document_id)


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return index_status(db)