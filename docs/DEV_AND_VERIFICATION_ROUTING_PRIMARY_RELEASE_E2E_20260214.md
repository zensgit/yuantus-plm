# Dev & Verification Report - Routing Primary+Release + MBOM Release E2E (2026-02-14)

This delivery adds/extends self-contained, evidence-grade Manufacturing verification scripts (API-only, no docker compose required):

- Routing: primary switch + release-diagnostics/release guardrails
- MBOM + Routing: primary uniqueness + routing release + MBOM release

## Changes

### 1) New self-contained verification script (Routing Primary+Release)

- New: `scripts/verify_routing_primary_release_e2e.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB and local storage.
  - Seeds identity + meta (admin superuser).
  - Scenario coverage:
    - create two routings in the same MBOM scope and validate primary uniqueness
    - switch primary via `PUT /api/v1/routings/{id}/primary`
    - release-diagnostics + release guardrails:
      - empty operations -> `routing_empty_operations` and release blocked
      - inactive workcenter referenced by an operation -> `workcenter_inactive` and release blocked
    - successful routing release + already-released guardrail

### 2) Extend existing MBOM + Routing E2E

- Updated: `scripts/verify_mbom_routing_e2e.sh`
  - Adds routing primary uniqueness + primary switch.
  - Adds routing release-diagnostics/release and MBOM release-diagnostics/release.

### 3) Optional wiring into regression suite

- `scripts/verify_all.sh`
  - Add optional suite: `RUN_ROUTING_PRIMARY_RELEASE_E2E=1` → `Routing Primary+Release (E2E)`.

### 4) Docs

- `docs/VERIFICATION.md`
  - Document `verify_routing_primary_release_e2e.sh` and `RUN_ROUTING_PRIMARY_RELEASE_E2E=1`.
  - Update MBOM + Routing section to include release coverage.
- `docs/VERIFICATION_RESULTS.md`
  - Record executed PASS runs with evidence paths.

## Verification (Executed)

```bash
bash scripts/verify_routing_primary_release_e2e.sh
bash scripts/verify_mbom_routing_e2e.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Routing Primary+Release:
  - Log: `tmp/verify_routing_primary_release_e2e_20260214-114321.log`
  - Payloads: `tmp/verify-routing-primary-release/20260214-114321/`
- MBOM + Routing (extended):
  - Log: `tmp/verify_mbom_routing_e2e_20260214-114343.log`
  - Payloads: `tmp/verify-mbom-routing/20260214-114343/`

