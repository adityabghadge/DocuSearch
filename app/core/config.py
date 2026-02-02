from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for DocuSearch.
    Loaded from .env (no secrets committed).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # Chunking (deterministic)
    CHUNK_SIZE_CHARS: int = 1200
    CHUNK_OVERLAP_CHARS: int = 150

    # Retrieval
    DEFAULT_TOP_K: int = 5

    # Embeddings
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Database
    DATABASE_URL: str

    # Qdrant
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION: str = "docusearch_chunks"
    QDRANT_DISTANCE: str = "cosine"

    # QA / LLM (optional, disabled by default)
    USE_LLM: bool = False


settings = Settings()