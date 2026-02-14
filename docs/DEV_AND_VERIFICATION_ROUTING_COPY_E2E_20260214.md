# Dev & Verification Report - Routing Copy API-only E2E Verification (2026-02-14)

This delivery adds a self-contained, evidence-grade verification for Manufacturing Routing copy (API-only, no docker compose required).

## Changes

### 1) New self-contained verification script

- New: `scripts/verify_routing_copy_e2e.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB and local storage.
  - Seeds identity + meta (admin superuser).
  - Exercises Routing copy workflow:
    - build a minimal EBOM (parent -> child) and create MBOM from EBOM
    - create routing and add 2 operations (including a WorkCenter reference)
    - copy routing + operations via `POST /api/v1/routings/{routing_id}/copy?new_name=...`
    - validate copied routing contract:
      - copied routing default `is_primary=false`
      - source routing remains `is_primary=true`
      - copied operations count + key fields are copied (operation_number/sequence/workcenter_code)

### 2) Optional wiring into regression suite

- `scripts/verify_all.sh`
  - Add optional suite `RUN_ROUTING_COPY_E2E=1` → `Routing Copy (E2E)`.

### 3) Docs

- `docs/VERIFICATION.md`
  - Document direct usage and `RUN_ROUTING_COPY_E2E=1` for `verify_all.sh`.
- `docs/VERIFICATION_RESULTS.md`
  - Record an executed PASS run with evidence paths.

## Verification (Executed)

```bash
bash scripts/verify_routing_copy_e2e.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_routing_copy_e2e_20260214-122501.log`
- Payloads: `tmp/verify-routing-copy/20260214-122501/`

