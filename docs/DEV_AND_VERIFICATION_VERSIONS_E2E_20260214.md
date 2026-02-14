# Dev & Verification Report - Versions Core API-only E2E Verification (2026-02-14)

This delivery adds a self-contained, evidence-grade verification for Versions core semantics (API-only, no docker compose required).

## Changes

### 1) New self-contained verification script

- New: `scripts/verify_versions_e2e.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB and local storage.
  - Seeds identity + meta (admin + viewer).
  - Exercises Versions core flows:
    - init/revise: `POST /api/v1/versions/items/{item_id}/init|revise`
    - checkout/checkin + lock contention (viewer blocked while admin has checkout): `POST /api/v1/versions/items/{item_id}/checkout|checkin`
    - tree/history: `GET /api/v1/versions/items/{item_id}/tree|history`
    - revision utils: `GET /api/v1/versions/revision/next|parse|compare`
    - iterations: `POST/GET /api/v1/versions/{version_id}/iterations`
    - compare versions property diffs: `GET /api/v1/versions/compare?v1=...&v2=...`
    - revision schemes: `POST/GET /api/v1/versions/schemes`

### 2) Version properties persistence fix

- `src/yuantus/meta_engine/version/service.py`
  - Fix JSON properties updates to always assign fresh dict objects (ensures SQLAlchemy persists changes for `ItemVersion.properties` and `Item.properties`).
  - Deep-copy properties when creating new versions/iterations to ensure snapshots are independent.

### 3) Optional wiring into regression suite

- `scripts/verify_all.sh`
  - Add optional suite `RUN_VERSIONS_E2E=1` → `Versions Core (E2E)`.

### 4) Docs

- `docs/VERIFICATION.md`
  - Document direct usage and `RUN_VERSIONS_E2E=1` for `verify_all.sh`.
- `docs/VERIFICATION_RESULTS.md`
  - Record an executed PASS run with evidence paths.

## Verification (Executed)

```bash
bash scripts/verify_versions_e2e.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_versions_e2e_20260214-154159.log`
- Payloads: `tmp/verify-versions/20260214-154159/`

