from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.qa import qa as qa_service

router = APIRouter()


class QAIn(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=settings.DEFAULT_TOP_K, ge=1, le=50)


@router.post("")
def qa_endpoint(payload: QAIn, db: Session = Depends(get_db)):
    out = qa_service(db, payload.question, payload.top_k)

    # Hard guard: always include sources key (even if empty list)
    if "sources" not in out:
        out["sources"] = []

    return out