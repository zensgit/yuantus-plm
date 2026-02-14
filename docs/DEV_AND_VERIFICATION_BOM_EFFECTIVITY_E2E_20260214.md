# Dev & Verification Report - BOM Effectivity API-only E2E Verification (2026-02-14)

This delivery adds a self-contained, evidence-grade verification for BOM effectivity (date-based) (API-only, no docker compose required).

## Changes

### 1) New self-contained verification script

- New: `scripts/verify_bom_effectivity_e2e.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB and local storage.
  - Seeds identity + meta (admin superuser + a non-superuser viewer user).
  - Exercises BOM effectivity:
    - add BOM lines with `effectivity_from/to` via `POST /api/v1/bom/{item_id}/children`
    - query effective BOM via `GET /api/v1/bom/{item_id}/effective?date=...`
    - validate returned child sets for TODAY/NEXT_WEEK/LAST_WEEK
  - Exercises RBAC:
    - configure a read-only PermissionSet for `Part` and `Part BOM`
    - viewer add BOM child is blocked (`403`)
    - viewer read effective BOM is allowed (`200`)
  - Exercises delete cascade behavior:
    - delete relationship via `DELETE /api/v1/bom/{parent_id}/children/{child_id}`
    - verify future effective BOM no longer includes the deleted child

### 2) Optional wiring into regression suite

- `scripts/verify_all.sh`
  - Add optional suite `RUN_BOM_EFFECTIVITY_E2E=1` → `BOM Effectivity (E2E)`.

### 3) Docs

- `docs/VERIFICATION.md`
  - Document direct usage and `RUN_BOM_EFFECTIVITY_E2E=1` for `verify_all.sh`.
- `docs/VERIFICATION_RESULTS.md`
  - Record an executed PASS run with evidence paths.

## Verification (Executed)

```bash
bash scripts/verify_bom_effectivity_e2e.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_bom_effectivity_e2e_20260214-145202.log`
- Payloads: `tmp/verify-bom-effectivity/20260214-145202/`

