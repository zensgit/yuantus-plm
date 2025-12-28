# YuantusPLM API Service Dockerfile
# Private Deployment: PostgreSQL + MinIO

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Optional pip mirror (set via build args)
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=pypi.org
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

# Copy source code FIRST (required for pip install)
COPY pyproject.toml README.md ./
COPY requirements.lock ./
COPY src/ ./src/
COPY plugins/ ./plugins/
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY vendor/wheels/ /wheels/

# Install dependencies (non-editable for production)
RUN if ls /wheels/*.whl >/dev/null 2>&1; then \
      PIP_NO_INDEX=1 PIP_FIND_LINKS=/wheels PIP_DEFAULT_TIMEOUT=600 PIP_RETRIES=20 \
      pip install --no-cache-dir -r requirements.lock; \
    else \
      PIP_DEFAULT_TIMEOUT=600 PIP_RETRIES=20 pip install --no-cache-dir -r requirements.lock; \
    fi
RUN if ls /wheels/*.whl >/dev/null 2>&1; then \
      PIP_NO_INDEX=1 PIP_FIND_LINKS=/wheels PIP_DEFAULT_TIMEOUT=600 PIP_RETRIES=20 \
      pip install --no-cache-dir --no-deps .; \
    else \
      PIP_DEFAULT_TIMEOUT=600 PIP_RETRIES=20 pip install --no-cache-dir --no-deps .; \
    fi

# Create data directory
RUN mkdir -p /app/data/storage

# Expose port
EXPOSE 7910

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7910/api/v1/health || exit 1

# Default environment variables
ENV YUANTUS_HOST=0.0.0.0 \
    YUANTUS_PORT=7910 \
    YUANTUS_ENVIRONMENT=production \
    YUANTUS_SCHEMA_MODE=migrations

# Run the API server
CMD ["yuantus", "start"]
