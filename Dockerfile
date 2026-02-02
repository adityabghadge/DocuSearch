FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies (needed for sentence-transformers + pypdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata first (Docker layer caching)
COPY pyproject.toml README.md /app/

# Copy application code
COPY app /app/app
COPY scripts /app/scripts
COPY samples /app/samples
COPY tests /app/tests

# Install Python deps
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir \
      fastapi==0.115.6 \
      "uvicorn[standard]==0.30.6" \
      pydantic==2.9.2 \
      pydantic-settings==2.6.1 \
      sqlalchemy==2.0.36 \
      "psycopg[binary]==3.2.3" \
      qdrant-client==1.12.1 \
      sentence-transformers==3.2.1 \
      numpy==2.1.3 \
      python-multipart==0.0.12 \
      pypdf==5.1.0 \
      httpx==0.27.2 \
      tenacity==9.0.0 \
      rich==13.9.4 \
      pytest==8.3.3 \
      pytest-asyncio==0.24.0 \
      pytest-cov==5.0.0 \
      requests==2.32.3

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]