# Delivery Dependencies & Requirements (2026-02-02)

## Runtime

- Docker Engine (20.10+ recommended)
- Docker Compose (v2 recommended)

## Optional

- PostgreSQL (if external DB is used)
- MinIO (if external object storage is used)
- TLS certificates (`certs/tls.crt`, `certs/tls.key`)

## Notes

- Environment templates are under `env/`. Copy to `env/.env` and fill in secrets.
- For offline delivery, load images from `images/` via `docker load -i`.
