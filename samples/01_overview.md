# DocuSearch Overview

DocuSearch is a Dockerized semantic document search system built with Python and FastAPI.
It ingests unstructured documents, chunks them deterministically, embeds chunks using all-MiniLM-L6-v2 (384 dims),
and stores vectors in Qdrant for low-latency similarity search.

Key ideas:
- Deduplicate documents via sha256 (idempotent uploads).
- Deterministic chunking: same input -> same chunk boundaries.
- Semantic retrieval: cosine similarity over embedding vectors.
- Q&A is grounded only in retrieved context and always includes citations.

Run requirements (fresh machine):
1) cp .env.example .env
2) docker compose up -d --build
3) docker compose exec api pytest -q
4) docker compose exec api python scripts/demo_run.py
5) docker compose exec api python scripts/evaluate.py