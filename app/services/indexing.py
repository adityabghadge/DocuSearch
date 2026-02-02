from __future__ import annotations

from typing import List

from qdrant_client.http.models import Distance, PointStruct, VectorParams
from sqlalchemy.orm import Session

from app.core.chunking import chunk_text
from app.core.config import settings
from app.core.embeddings import embed_texts, embedding_dim
from app.core.retrieval import get_qdrant
from app.db.models import Chunk, Document
import uuid


def ensure_collection() -> None:
    client = get_qdrant()
    dim = embedding_dim()

    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        distance = Distance.COSINE if settings.QDRANT_DISTANCE.lower() == "cosine" else Distance.DOT
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=distance),
        )


def index_document(db: Session, document_id: int) -> dict:
    ensure_collection()

    doc = db.query(Document).filter(Document.id == document_id).one()

    chunks = chunk_text(
        doc.extracted_text,
        chunk_size_chars=settings.CHUNK_SIZE_CHARS,
        overlap_chars=settings.CHUNK_OVERLAP_CHARS,
    )

    existing = {
        c.chunk_index: c
        for c in db.query(Chunk).filter(Chunk.document_id == document_id).all()
    }

    to_embed: List[str] = []
    to_upsert_rows: List[Chunk] = []

    for ch in chunks:
        row = existing.get(ch.chunk_index)
        if row is None:
            row = Chunk(
                document_id=document_id,
                chunk_index=ch.chunk_index,
                text=ch.text,
                char_start=ch.char_start,
                char_end=ch.char_end,
                token_count_est=ch.token_count_est,
                qdrant_point_id=None,
            )
            db.add(row)
            db.flush()
        else:
            # If extraction changes, update stored fields (determinism should keep these stable)
            row.text = ch.text
            row.char_start = ch.char_start
            row.char_end = ch.char_end
            row.token_count_est = ch.token_count_est

        # Stable, reproducible vector point id:
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}:{ch.chunk_index}"))
        row.qdrant_point_id = point_id

        to_embed.append(ch.text)
        to_upsert_rows.append(row)

    db.commit()

    vectors = embed_texts(to_embed).tolist()

    points: list[PointStruct] = []
    for row, vec in zip(to_upsert_rows, vectors):
        points.append(
            PointStruct(
                id=row.qdrant_point_id,
                vector=vec,
                payload={
                    "chunk_id": row.id,
                    "document_id": row.document_id,
                    "chunk_index": row.chunk_index,
                },
            )
        )

    client = get_qdrant()
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)

    return {"document_id": document_id, "chunks_indexed": len(points)}


def reindex_all(db: Session) -> dict:
    ensure_collection()

    client = get_qdrant()
    # Drop + recreate collection to guarantee a clean rebuild.
    client.delete_collection(collection_name=settings.QDRANT_COLLECTION)
    ensure_collection()

    docs = db.query(Document).all()

    total = 0
    for d in docs:
        out = index_document(db, d.id)
        total += out["chunks_indexed"]

    return {"documents": len(docs), "chunks_indexed": total}


def index_status(db: Session) -> dict:
    docs = db.query(Document).count()
    chunks = db.query(Chunk).count()
    indexed = db.query(Chunk).filter(Chunk.qdrant_point_id.isnot(None)).count()
    return {"documents": docs, "chunks": chunks, "indexed_chunks": indexed}