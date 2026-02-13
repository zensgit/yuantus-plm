# Dev & Verification Report - BOM Compare API-only E2E Verification (2026-02-14)

This delivery adds a self-contained, evidence-grade verification for BOM Compare (API-only, no docker compose required).

## Changes

### 1) New self-contained verification script

- New: `scripts/verify_bom_compare_e2e.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB and local storage.
  - Seeds identity + meta (admin superuser).
  - Builds two parent BOMs (left/right) with:
    - add/remove/change lines
    - substitutes + effectivity on the changed line
  - Verifies `/api/v1/bom/compare` summary and change-field contracts.
  - Exercises compare_mode variants: `only_product`, `num_qty`, `summarized`.

### 2) Fix: SQLite-compatible Effectivity.created_at default

- `src/yuantus/meta_engine/models/effectivity.py`
  - Change `Effectivity.created_at` server default from `now()` to `CURRENT_TIMESTAMP`.
  - Rationale: with SQLite, `server_default="now()"` can be persisted as a literal string (`'now()'`), which then breaks DateTime parsing and causes `Invalid isoformat string: 'now()'` during BOM effectivity flows.

### 3) Optional wiring into regression suite

- `scripts/verify_all.sh`
  - Add optional suite `RUN_BOM_COMPARE_E2E=1` → `BOM Compare (E2E)`.

### 4) Docs

- `docs/VERIFICATION.md`
  - Document direct usage and `RUN_BOM_COMPARE_E2E=1` for `verify_all.sh`.
- `docs/VERIFICATION_RESULTS.md`
  - Record an executed PASS run with evidence paths.

## Verification (Executed)

```bash
bash scripts/verify_bom_compare_e2e.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_bom_compare_e2e_20260214-013350.log`
- Payloads: `tmp/verify-bom-compare/20260214-013350/`

