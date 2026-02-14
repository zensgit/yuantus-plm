# Dev & Verification Report - ECO Advanced API-only E2E Verification (2026-02-14)

This delivery adds a self-contained, evidence-grade verification for ECO Advanced full flow (API-only, no docker compose required).

## Changes

### 1) New self-contained verification script

- New: `scripts/verify_eco_advanced_e2e.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB and local storage.
  - Seeds identity + meta (admin + viewer).
  - Exercises ECO Advanced end-to-end:
    - stage + stage move + overdue notify
    - approve + apply (with apply-diagnostics pass)
    - where-used impact (assembly -> product) + BOM diff guardrails
    - impact analysis (include files + bom diff + version diffs)
    - impact export (csv/xlsx/pdf)
    - batch approvals (admin ok, viewer denied)

### 2) Optional wiring into regression suite

- `scripts/verify_all.sh`
  - Add optional suite `RUN_ECO_ADVANCED_E2E=1` → `ECO Advanced (E2E)`.

### 3) Docs

- `docs/VERIFICATION.md`
  - Document direct usage and `RUN_ECO_ADVANCED_E2E=1` for `verify_all.sh`.
- `docs/VERIFICATION_RESULTS.md`
  - Record an executed PASS run with evidence paths.

## Verification (Executed)

```bash
bash scripts/verify_eco_advanced_e2e.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_eco_advanced_e2e_20260214-160347.log`
- Payloads: `tmp/verify-eco-advanced/20260214-160347/`

