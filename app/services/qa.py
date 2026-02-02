from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.services.search import semantic_search


def grounded_answer(question: str, sources: List[dict]) -> str:
    """
    RAG-lite, grounded response:
    - We DO NOT invent facts.
    - We assemble an answer only from retrieved snippets.
    - If there's not enough info, we say so.
    """
    if not sources:
        return "I couldn't find that in the uploaded documents."

    snippets = [s.get("snippet", "") for s in sources[:5]]
    joined = " ".join([s for s in snippets if s]).strip()

    if not joined:
        return "I couldn't find that in the uploaded documents."

    # Keep it compact for API responses / demos.
    return joined[:900]


def qa(db: Session, question: str, top_k: int) -> dict:
    retrieval = semantic_search(db, question, top_k=top_k)
    sources = retrieval["results"]

    answer = grounded_answer(question, sources)

    # Enforce citations: always return sources[] (even if empty)
    return {
        "question": question,
        "answer": answer,
        "retrieval_ms": retrieval["retrieval_ms"],
        "sources": sources if sources else [],
    }