from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.search import semantic_search

router = APIRouter()


@router.get("")
def search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(settings.DEFAULT_TOP_K, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return semantic_search(db, q, top_k=top_k)