# YuantusPLM API Service Dockerfile
# Private Deployment: PostgreSQL + MinIO

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source code FIRST (required for pip install)
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY plugins/ ./plugins/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Install dependencies (non-editable for production)
RUN pip install --no-cache-dir .

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
