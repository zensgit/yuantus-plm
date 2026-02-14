# Dev & Verification Report - Run H API-only E2E Verification (2026-02-14)

This delivery adds a self-contained, evidence-grade verification for Run H (Core APIs) smoke coverage (API-only, no docker compose required).

## Changes

### 1) New self-contained verification script

- New: `scripts/verify_run_h_e2e.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB and local storage.
  - Seeds identity + meta (admin superuser).
  - Exercises core APIs:
    - health: `GET /api/v1/health`
    - meta metadata: `GET /api/v1/aml/metadata/Part`
    - AML add/get: `POST /api/v1/aml/apply`
    - Search: `GET /api/v1/search/?q=...`
    - RPC: `POST /api/v1/rpc/`
    - File upload/download: `POST /api/v1/file/upload`, `GET /api/v1/file/{id}/download`
    - BOM effective: `GET /api/v1/bom/{item_id}/effective`
    - Plugins: `GET /api/v1/plugins`, `GET /api/v1/plugins/demo/ping`
    - ECO full flow: create/new-revision/approve/apply
    - Versions history/tree: `GET /api/v1/versions/items/{item_id}/history|tree`
    - Integrations health: `GET /api/v1/integrations/health`

### 2) Optional wiring into regression suite

- `scripts/verify_all.sh`
  - Add optional suite `RUN_RUN_H_E2E=1` → `Run H (E2E)`.

### 3) Docs

- `docs/VERIFICATION.md`
  - Document direct usage and `RUN_RUN_H_E2E=1` for `verify_all.sh`.
- `docs/VERIFICATION_RESULTS.md`
  - Record an executed PASS run with evidence paths.

## Verification (Executed)

```bash
bash scripts/verify_run_h_e2e.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_run_h_e2e_20260214-161527.log`
- Payloads: `tmp/verify-run-h/20260214-161527/`

