from __future__ import annotations

import time
from typing import Any, Iterable

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.embeddings import embed_texts
from app.db.models import Chunk


def _make_snippet(text: str, max_len: int = 240) -> str:
    if not text:
        return ""
    s = " ".join(text.split())  # normalize whitespace/newlines
    return s[:max_len]


def semantic_search(db: Session, query: str, top_k: int = 5) -> dict[str, Any]:
    """
    Vector similarity search via Qdrant.

    Important design choice:
    - Qdrant stores vectors + minimal payload (ids / metadata).
    - Postgres is the source of truth for chunk text.
    - Snippets are generated from Postgres to guarantee citations are never empty.
    """
    t0 = time.perf_counter()

    # Embed query (local sentence-transformers)
    vec = embed_texts([query])[0].tolist()

    client = QdrantClient(url=settings.QDRANT_URL)
    hits = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=vec,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
        query_filter=Filter(must=[]),  # placeholder; future metadata filtering
    )

    # Extract chunk_ids + scores from qdrant hits
    scored_chunk_ids: list[tuple[int, float]] = []
    for h in hits:
        payload = h.payload or {}
        chunk_id = payload.get("chunk_id")
        if chunk_id is None:
            continue
        try:
            chunk_id_int = int(chunk_id)
        except (TypeError, ValueError):
            continue
        scored_chunk_ids.append((chunk_id_int, float(h.score)))

    # Fetch chunks from Postgres (source of truth for text)
    chunk_map: dict[int, Chunk] = {}
    if scored_chunk_ids:
        ids = [cid for cid, _ in scored_chunk_ids]
        rows = db.query(Chunk).filter(Chunk.id.in_(ids)).all()
        chunk_map = {c.id: c for c in rows}

    results: list[dict[str, Any]] = []
    for chunk_id, score in scored_chunk_ids:
        ch = chunk_map.get(chunk_id)
        if not ch:
            # If DB row missing, still return the id/score for transparency
            results.append(
                {
                    "document_id": None,
                    "chunk_id": chunk_id,
                    "chunk_index": None,
                    "score": score,
                    "snippet": "",
                }
            )
            continue

        results.append(
            {
                "document_id": ch.document_id,
                "chunk_id": ch.id,
                "chunk_index": ch.chunk_index,
                "score": score,
                "snippet": _make_snippet(ch.text),
            }
        )

    retrieval_ms = (time.perf_counter() - t0) * 1000.0
    return {"query": query, "top_k": top_k, "retrieval_ms": retrieval_ms, "results": results}


def keyword_baseline_search(db: Session, query: str, top_k: int = 5) -> dict[str, Any]:
    """
    Keyword baseline using Postgres full-text search + ts_rank.
    Used only in evaluation harness, not the main product surface.
    """
    t0 = time.perf_counter()

    vec = func.to_tsvector("english", Chunk.text)
    qry = func.plainto_tsquery("english", query)
    rank = func.ts_rank(vec, qry).label("rank")

    rows = (
        db.query(Chunk, rank)
        .filter(vec.op("@@")(qry))
        .order_by(rank.desc())
        .limit(top_k)
        .all()
    )

    results: list[dict[str, Any]] = []
    for ch, r in rows:
        results.append(
            {
                "document_id": ch.document_id,
                "chunk_id": ch.id,
                "chunk_index": ch.chunk_index,
                "score": float(r),
                "snippet": _make_snippet(ch.text),
            }
        )

    retrieval_ms = (time.perf_counter() - t0) * 1000.0
    return {"query": query, "top_k": top_k, "retrieval_ms": retrieval_ms, "results": results}