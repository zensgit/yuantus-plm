# Release Notes v0.1.2

This release adds S12 Configuration/Variant BOM support and completes full regression validation.

## Quick Start (3 steps)

### 1) Install / Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2) Start (Postgres + MinIO)

```bash
docker compose up -d postgres minio
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:5434/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:9000'

yuantus db upgrade
yuantus init-storage
yuantus start --port 7910
```

### 3) Verify

```bash
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

## References

- Changelog: `CHANGELOG.md`
- Verification summary: `docs/VERIFICATION_RESULTS.md`
