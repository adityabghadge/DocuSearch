from fastapi import FastAPI

from app.core.logging import configure_logging
from app.db.session import init_db
from app.api.routers import documents, index, search, qa

configure_logging()

app = FastAPI(
    title="DocuSearch",
    description="Semantic Document Search & Knowledge Retrieval (RAG-lite)",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


# Routers
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(index.router, prefix="/index", tags=["index"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(qa.router, prefix="/qa", tags=["qa"])