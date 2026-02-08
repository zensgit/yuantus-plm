# Dev & Verification Report - Release Orchestration (Plan + Execute) (2026-02-08)

This delivery adds an evidence-grade, admin-only "release orchestration" API that can:

1. Build a release plan for an Item (dry-run view).
2. Execute the plan across related resources with structured per-step results.

Execution order is `routing -> mbom -> baseline` (routing may unblock MBOM release rules that require at least one released routing).

## API

- Plan (dry-run):
  - `GET /api/v1/release-orchestration/items/{item_id}/plan?ruleset_id=default`
- Execute:
  - `POST /api/v1/release-orchestration/items/{item_id}/execute`
    - Body:
      - `ruleset_id` (default: `default`)
      - `include_routings` (default: `true`)
      - `include_mboms` (default: `true`)
      - `include_baselines` (default: `false`)
      - `dry_run` (default: `false`)
      - `continue_on_error` (default: `false`)
      - `rollback_on_failure` (default: `false`)
      - `baseline_force` (default: `false`)
        - When `true`, baseline steps may execute even if baseline release diagnostics have errors (baseline-only). This does not bypass the e-sign gate.

## E-Sign Gate (Baseline Only)

When `include_baselines=true`, baseline release execution is blocked if an e-sign manifest exists for the Item and `is_complete=false`.

- Plan: baseline steps will show `action=requires_esign` when blocked.
- Execute: baseline results will show `status=blocked_esign_incomplete` when blocked.

## Implementation

- Router: `src/yuantus/meta_engine/web/release_orchestration_router.py`
- App wiring: `src/yuantus/api/app.py`
- Uses existing services:
  - `ReleaseReadinessService` for resource selection and post-run summary
  - `RoutingService`, `MBOMService`, `BaselineService` for diagnostics + release execution

## Tests

- Unit tests (non-DB):
  - `src/yuantus/meta_engine/tests/test_release_orchestration_router.py`
- Playwright (API-only):
  - `playwright/tests/release_orchestration.spec.js`

## Verification

- Targeted pytest:
  - `./.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_release_orchestration_router.py`
- Playwright:
  - `npx playwright test playwright/tests/release_orchestration.spec.js`
- Strict gate evidence (PASS):
  - `docs/DAILY_REPORTS/STRICT_GATE_20260208-105603.md`

## Notes

- Rollback is best-effort and only applies to resources released during the current orchestration run:
  - MBOM rollback steps are recorded as `kind=mbom_reopen`.
  - Routing rollback steps are recorded as `kind=routing_reopen`.
