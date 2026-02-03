# Baseline List Filters — Design & Development (2026-02-03)

## Background
Phase 4 (baseline enhancement) requires multi-type baselines and richer query capability.
The existing `GET /api/v1/baselines` only supported `root_item_id`, `root_version_id`, and `created_by_id`,
which is insufficient for UI filtering by type/scope/state/effective date.

## Scope
Add optional list filters to the baselines list endpoint:
- `baseline_type`
- `scope`
- `state`
- `effective_from`
- `effective_to`

No schema changes; only query-level filters.

## API Design
Endpoint: `GET /api/v1/baselines`

New optional query parameters:
- `baseline_type`: string
- `scope`: string
- `state`: string
- `effective_from`: datetime
- `effective_to`: datetime

Behavior:
- Each param is optional; omitted params do not filter.
- `effective_from` / `effective_to` are normalized to UTC-naive before filtering.
- Auth/tenant scope remains unchanged.

## Implementation Notes
- `BaselineService.list_baselines` now accepts and applies the new filters.
- `baseline_router.list_baselines` exposes query params and passes them through.
- Added unit test to verify filters are applied in the query chain.

## Verification
- Command: `./.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_baseline_enhanced.py`
- Result: PASS (5 passed, 2 warnings)

## Files Changed
- `src/yuantus/meta_engine/services/baseline_service.py`
- `src/yuantus/meta_engine/web/baseline_router.py`
- `src/yuantus/meta_engine/tests/test_baseline_enhanced.py`
- `docs/VERIFICATION_RESULTS.md`
