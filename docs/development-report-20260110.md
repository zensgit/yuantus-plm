# Development Report (2026-01-10)

## Summary
- Hardened Alembic default database URL resolution to avoid placeholder driver URLs.

## Changes
- `migrations/env.py`: fall back to `sqlite:///yuantus_dev.db` when `sqlalchemy.url` is the placeholder `driver://...`.

## Rationale
- Running `yuantus db upgrade` without `YUANTUS_DATABASE_URL` was failing due to the placeholder URL in `alembic.ini`.
- The fallback keeps local dev usage predictable while still honoring explicit environment configuration.
