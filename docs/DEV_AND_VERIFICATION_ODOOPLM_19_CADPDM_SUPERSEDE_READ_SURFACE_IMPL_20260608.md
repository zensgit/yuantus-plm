# Superseded Read-Surface Implementation Verification

Date: 2026-06-08

## Scope

Implements the doc-locked Superseded read surface from
`DEVELOPMENT_ODOOPLM_19_CADPDM_SUPERSEDE_READ_SURFACE_TASKBOOK_20260607.md`.
This slice is read-only: no migration, no B1 state-machine change, and no
server-side `?status=` filter.

## Implementation

- Added `VersionService.list_versions(item_id)` with an item-existence check,
  stable ordering by `generation ASC, created_at ASC, id ASC`, and the locked
  first-match `lifecycle_status` taxonomy:
  `historical_released`, `active_released`, `in_work`, `draft`.
- Added `GET /api/v1/versions/items/{item_id}/versions` on the existing
  `version_lifecycle_router`, parallel to `/history`, using the inherited
  `get_current_user_id` dependency (`get_current_user_id_optional` alias).
- Preserved raw flags in the response, including `is_current`, `is_released`,
  and `is_superseded`; `is_superseded` is not a peer status.
- Updated route-count contracts for the live baseline: `706 -> 707`, and added
  the new route to `test_version_lifecycle_router_contracts.MOVED_ROUTES`.

## Verification

- `test_version_supersede_read_surface.py` covers:
  - `historical_released`, `active_released`, `in_work`, and `draft`
    classification.
  - raw `is_superseded` flag serialization.
  - top-level `is_under_modification`.
  - stable ordering by `generation`, `created_at`, then `id`.
  - missing item -> 404 through the router, not an empty list.
  - v1 has no server-side `?status=` filter; undeclared params do not filter.
- Test file is registered in both `.github/workflows/ci.yml` and the no-DB
  allowlist in `conftest.py`.
- No Alembic migration was added; implementation was grounded against the live
  single Alembic head `b1_supersede_001`.

## Expected Local Checks

- `PYTHONPATH=src .venv-wp13/bin/pytest src/yuantus/meta_engine/tests/test_version_supersede_read_surface.py`
- `PYTHONPATH=src .venv-wp13/bin/pytest src/yuantus/meta_engine/tests/test_version_lifecycle_router_contracts.py src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py src/yuantus/meta_engine/tests/test_breakage_design_loopback_metrics.py src/yuantus/meta_engine/tests/test_tier_b_3_breakage_design_loopback_portfolio_contract.py`
- `git diff --check`
