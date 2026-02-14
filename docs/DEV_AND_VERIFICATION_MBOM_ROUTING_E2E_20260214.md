# Dev & Verification Report - MBOM + Routing API-only E2E Verification (2026-02-14)

This delivery adds a self-contained, evidence-grade verification for Manufacturing MBOM + Routing (API-only, no docker compose required).

## Changes

### 1) New self-contained verification script

- New: `scripts/verify_mbom_routing_e2e.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB and local storage.
  - Seeds identity + meta (admin superuser).
  - Exercises Manufacturing MBOM + Routing:
    - build a minimal EBOM (parent -> child)
    - create MBOM from EBOM via `POST /api/v1/mboms/from-ebom`
    - validate MBOM structure via `GET /api/v1/mboms/{mbom_id}`
    - create routing + operations via `POST /api/v1/routings` + `POST /api/v1/routings/{id}/operations`
    - calculate time/cost via `POST /api/v1/routings/{id}/calculate-time|calculate-cost`

### 2) Optional wiring into regression suite

- `scripts/verify_all.sh`
  - Add optional suite `RUN_MBOM_ROUTING_E2E=1` → `MBOM + Routing (E2E)`.

### 3) Docs

- `docs/VERIFICATION.md`
  - Document direct usage and `RUN_MBOM_ROUTING_E2E=1` for `verify_all.sh`.
- `docs/VERIFICATION_RESULTS.md`
  - Record an executed PASS run with evidence paths.

## Verification (Executed)

```bash
bash scripts/verify_mbom_routing_e2e.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_mbom_routing_e2e_20260214-105622.log`
- Payloads: `tmp/verify-mbom-routing/20260214-105622/`

