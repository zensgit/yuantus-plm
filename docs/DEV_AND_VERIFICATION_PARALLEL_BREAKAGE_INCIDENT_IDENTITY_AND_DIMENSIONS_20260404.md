# Dev / Verification: Breakage Incident Identity and Dimensions

## Date

2026-04-04

## Scope

Verification for:

- `Breakage Incident Identity and Dimensions`

## Files Changed

- `migrations/versions/c4d5e6f7a8b9_add_breakage_incident_identity_dimensions.py`
- `src/yuantus/meta_engine/models/parallel_tasks.py`
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

## Verification Commands

1. `pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_breakage_tasks.py -k 'breakage or helpdesk or incident'`
2. `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile src/yuantus/meta_engine/models/parallel_tasks.py src/yuantus/meta_engine/services/parallel_tasks_service.py src/yuantus/meta_engine/web/parallel_tasks_router.py src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_breakage_tasks.py migrations/versions/c4d5e6f7a8b9_add_breakage_incident_identity_dimensions.py`
3. `git diff --check`

## Results

| Command | Result |
|--------|--------|
| pytest targeted breakage/helpdesk suites | `95 passed, 91 deselected` |
| py_compile | clean |
| git diff --check | clean |

## Verified Outcomes

- new incident contract fields are wired:
  - `incident_code`
  - `bom_id`
  - `mbom_id`
  - `routing_id`
- legacy aliases still remain available:
  - `version_id`
  - `production_order_id`
- `group_by=bom_id` is supported
- `metrics` / `cockpit` now include `by_bom_id` and `top_bom_ids`
- router create/list surfaces now expose normalized fields

## Remaining Work

This package intentionally did not implement:

- latest helpdesk ticket summary projection on incident rows

That remains the next package in the line.
