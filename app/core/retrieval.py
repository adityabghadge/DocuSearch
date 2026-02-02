from __future__ import annotations

from time import perf_counter

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter

from app.core.config import settings


def get_qdrant() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


def vector_search(
    query_vector: list[float],
    top_k: int,
    document_id: int | None = None,
) -> tuple[list[tuple[str, float]], float]:
    """
    Returns:
      - list of (chunk_id, score)
      - retrieval_ms for the vector lookup itself
    """
    client = get_qdrant()

    flt: Filter | None = None
    if document_id is not None:
        # payload contains document_id
        flt = Filter(must=[{"key": "document_id", "match": {"value": document_id}}])

    t0 = perf_counter()
    hits = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
        query_filter=flt,
    )
    retrieval_ms = (perf_counter() - t0) * 1000.0

    out: list[tuple[str, float]] = []
    for h in hits:
        payload = h.payload or {}
        out.append((str(payload.get("chunk_id")), float(h.score)))

    return out, retrieval_ms