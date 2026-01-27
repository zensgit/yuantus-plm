# CAD Extractor Service (Design)

## Goal
Validate the standalone CAD extractor microservice via `/api/v1/extract`.

## Flow
1. Health check `GET /health`.
2. Upload sample file to `POST /api/v1/extract`.
3. Verify response contains `ok=true`, `attributes.file_ext`, and `attributes.file_size_bytes`.

## Runtime
- Default base URL: `http://127.0.0.1:8200`
- Optional auth: `CAD_EXTRACTOR_SERVICE_TOKEN`
- Optional auto-start: docker compose profile `cad-extractor`

## Verification
- Script: `scripts/verify_cad_extractor_service.sh`
- Report: `docs/VERIFICATION_CAD_EXTRACTOR_SERVICE_20260127.md`
