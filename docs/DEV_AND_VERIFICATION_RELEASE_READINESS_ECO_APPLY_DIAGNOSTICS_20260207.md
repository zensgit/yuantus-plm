# Dev & Verification Report - Release Readiness + ECO Apply Diagnostics + Ruleset Directory (2026-02-07)

This delivery extends the "strategy-based validation + diagnostics" pattern beyond releases and adds an evidence-grade cross-domain readiness summary.

Goals:

- Provide a single endpoint to summarize **release readiness** across Manufacturing (MBOM/Routing), Baselines, and E-Sign manifest status.
- Add ECO apply diagnostics (side-effect-free) and wire it into the apply endpoint as a precheck gate (unless forced).
- Add a ruleset directory endpoint so operators can introspect supported kinds/rulesets/rules (built-in + configured).

## API

New endpoints:

- `GET /api/v1/release-validation/rulesets`
- `GET /api/v1/eco/{eco_id}/apply-diagnostics?ruleset_id=default`
- `GET /api/v1/release-readiness/items/{item_id}?ruleset_id=readiness`

Enhanced endpoint:

- `POST /api/v1/eco/{eco_id}/apply?ruleset_id=default&force=false&ignore_conflicts=false`
  - `force=true`: bypass diagnostics gate.
  - `force=false`: block apply with `400` if diagnostics return any `errors`.

## Configuration

Ruleset environment override (unchanged):

- `YUANTUS_RELEASE_VALIDATION_RULESETS_JSON`

New/extended kinds and built-in rulesets:

- `eco_apply` (new kind; `default` ruleset)
- `routing_release` / `mbom_release` / `baseline_release`: built-in `readiness` ruleset (excludes `*.not_already_released`)

## Implementation

- Rulesets:
  - `src/yuantus/meta_engine/services/release_validation.py`
- Ruleset directory router:
  - `src/yuantus/meta_engine/web/release_validation_router.py`
- ECO apply diagnostics (side-effect free) + apply gating:
  - `src/yuantus/meta_engine/services/eco_service.py`
  - `src/yuantus/meta_engine/web/eco_router.py`
- Release readiness summary:
  - `src/yuantus/meta_engine/services/release_readiness_service.py`
  - `src/yuantus/meta_engine/web/release_readiness_router.py`
  - `src/yuantus/api/app.py` (router wiring)

## Tests

- New unit tests (mocked, non-DB):
  - `src/yuantus/meta_engine/tests/test_release_validation_directory.py`
  - `src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py`
  - `src/yuantus/meta_engine/tests/test_release_readiness_router.py`
- Non-DB allowlist updated:
  - `conftest.py`

## Verification

- Strict gate report (PASS):
  - `docs/DAILY_REPORTS/STRICT_GATE_20260207-164556.md`

