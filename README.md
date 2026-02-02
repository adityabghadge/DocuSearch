# DocuSearch

**Semantic Document Search & Knowledge Retrieval System (RAG-lite)**

DocuSearch is a production-style, Dockerized backend system built with **Python + FastAPI** that ingests unstructured documents, deterministically chunks and embeds them, indexes vectors in **Qdrant**, and serves **low-latency semantic search** and a **grounded Q&A API with citations**.


---

## Architecture (High Level)

```
Client
  |
  |  /documents/*   /index/*   /search   /qa
  v
FastAPI (api)
  |
  +--> PostgreSQL (documents, chunks, logs)
  |
  +--> Qdrant (vector search)
  |
  +--> sentence-transformers (all-MiniLM-L6-v2, 384 dims)
```

---

## Core Features

- Ingest `.txt`, `.md` (PDF supported via pypdf)
- Deduplicate documents by **sha256** (idempotent uploads)
- **Deterministic chunking** (same input → same chunks)
- Vector-based semantic search with `retrieval_ms` reported
- Grounded Q&A: answers constructed only from retrieved chunks
- **100% citations**: every `/qa` response includes `sources[]`
- Evaluation harness comparing semantic vs keyword baseline
- Reproducible indexing across Docker rebuilds
- Unit + integration tests

---

## Tech Stack

- API: FastAPI  
- Database: PostgreSQL + SQLAlchemy  
- Embeddings: sentence-transformers (`all-MiniLM-L6-v2`, 384 dims)  
- Vector Store: Qdrant  
- Containers: Docker + Docker Compose  
- Testing: pytest  

---

## Quickstart (Fresh Machine)

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api pytest -q
docker compose exec api python scripts/demo_run.py
docker compose exec api python scripts/evaluate.py
```

---

## API Usage

### Upload a document
```bash
curl -F "file=@samples/01_overview.md" http://localhost:8000/documents/upload
```

### Upload raw text
```bash
curl -X POST http://localhost:8000/documents/text   -H "Content-Type: application/json"   -d '{"filename":"note.txt","content_type":"text/plain","text":"hello world"}'
```

### Reindex everything
```bash
curl -X POST http://localhost:8000/index/reindex
```

### Semantic search
```bash
curl "http://localhost:8000/search?q=deterministic%20chunking&top_k=5"
```

### Q&A (always includes citations)
```bash
curl -X POST http://localhost:8000/qa   -H "Content-Type: application/json"   -d '{"question":"How is deduplication implemented?","top_k":5}'
```

Swagger UI:
- http://localhost:8000/docs

---

## Proof Mapping

### 1) 1,000+ chunks indexed
- Run `scripts/demo_run.py`
- Prints document + chunk counts (≥1100 chunks)

### 2) <200ms semantic retrieval latency
- `/search` responses include `retrieval_ms`
- Demo prints avg / p50 / p95 latency

### 3) Semantic relevance improvement (~30–40%)
- Run `scripts/evaluate.py`
- Table compares **semantic vs keyword baseline** (hit@k, MRR, precision@k)

### 4) 100% citations
- Every `/qa` response includes `sources[]`
- Enforced at service + API layer

### 5) Noise reduction via tuning (~30%)
- `evaluate.py` prints a tuning table
- Compares different `top_k` values using `irrelevant@k`

### 6) Reproducibility across rebuilds
```bash
docker compose down -v
docker compose up -d --build
docker compose exec api python scripts/demo_run.py
```
- Stable chunking + stable vector IDs ensure consistent retrieval

---

## Evaluation Methodology

To ensure relevance and performance claims are honest and reproducible, DocuSearch includes a lightweight evaluation harness (`scripts/evaluate.py`).

- Queries and expected source documents are defined in `scripts/eval_cases.json`
- Both **keyword baseline** (PostgreSQL full-text search) and **semantic vector search** are executed
- A result is relevant if its document filename matches the labeled `expected_source`
- Metrics reported: **hit@k**, **MRR**, **precision@k**, **average retrieval latency**
- A tuning experiment evaluates retrieval noise via **irrelevant@k**

This approach favors transparency and repeatability over opaque scoring.

---

## Screenshots (Proof of Claims)

Screenshots are stored in the top-level `screenshots/` directory.

1. **Demo run**
   - `screenshots/01_demo_run.png`
   - Chunk count, latency summary, QA with citations

2. **Evaluation results**
   - `screenshots/02_evaluation.png`
   - Semantic vs keyword metrics and tuning table

3. **Q&A API response**
   - `screenshots/03_qa_response.png`
   - JSON showing answer, `retrieval_ms`, and `sources[]`

4. **Swagger UI**
   - `screenshots/04_swagger_ui.png`
   - OpenAPI documentation and schemas

---

## Repo Structure

```
app/
  api/routers/
  core/
  db/
  services/
scripts/
samples/
tests/
screenshots/
docker-compose.yml
Dockerfile
.env.example
README.md
pyproject.toml
```

---

## Notes on Determinism

- Chunking uses character offsets (not tokens)
- Qdrant point IDs are stable: `{document_id}:{chunk_index}`
- Identical inputs produce identical embeddings and retrieval results

---

## Notes & Limitations

Evaluation uses **document-level relevance labels** (expected source documents) rather than chunk-level annotations to ensure stability across re-indexing and fresh Docker rebuilds.

---

## License

MIT
