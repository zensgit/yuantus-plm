# Dev & Verification Report - P4 Baseline Release Diagnostics (2026-02-07)

This delivery extends the "strategy-based release validation + diagnostics" pattern to **Baselines (P4)**.

Goals:

- Provide a structured, repeatable precheck endpoint for baseline release (collect multiple failures in one call).
- Allow ruleset selection via `ruleset_id` (built-in default + optional configured rulesets).
- Keep diagnostics side-effect free (no baseline mutation/commit from diagnostics calls).

## API

New endpoint:

- `GET /api/v1/baselines/{baseline_id}/release-diagnostics?ruleset_id=default`

Enhanced endpoint:

- `POST /api/v1/baselines/{baseline_id}/release?ruleset_id=default`
  - Existing request body kept: `{"force": false}`
  - Behavior:
    - `force=true`: bypass diagnostics and release checks.
    - `force=false`: block release with `400` if diagnostics return any `errors`.

Response shape aligns with manufacturing release diagnostics:

- `{ok, resource_type, resource_id, ruleset_id, errors[], warnings[]}`

## Configuration

Optional environment override:

- `YUANTUS_RELEASE_VALIDATION_RULESETS_JSON`

Supported kinds now include:

- `routing_release`
- `mbom_release`
- `baseline_release` (new)

## Implementation

- Shared response models (reused across routers):
  - `src/yuantus/meta_engine/web/release_diagnostics_models.py`
- Manufacturing router refactor to use shared models:
  - `src/yuantus/meta_engine/web/manufacturing_router.py`
- Baseline ruleset support:
  - `src/yuantus/meta_engine/services/release_validation.py`
- Baseline diagnostics (side-effect free):
  - `src/yuantus/meta_engine/services/baseline_service.py` (`BaselineService.get_release_diagnostics`)
- Baseline router endpoints:
  - `src/yuantus/meta_engine/web/baseline_router.py`

## Tests

- New unit tests (mocked, non-DB):
  - `src/yuantus/meta_engine/tests/test_baseline_release_diagnostics.py`
- Non-DB allowlist updated to ensure targeted runs collect the new test file:
  - `conftest.py`

## Verification

- Strict gate report (PASS):
  - `docs/DAILY_REPORTS/STRICT_GATE_20260207-150747.md`

