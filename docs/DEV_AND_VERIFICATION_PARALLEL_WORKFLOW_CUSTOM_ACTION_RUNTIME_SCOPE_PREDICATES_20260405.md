# Verification: Workflow Custom Action Runtime Scope Predicates

## Date

2026-04-05

## Scope

Verified runtime scope predicate support for workflow custom actions, including
`workflow_map_id`, `stage_id`, and `eco_priority`.

## Commands

1. `pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py -k 'workflow or custom_action or trigger_phase or set_eco_priority'`
   Result: `12 passed, 178 deselected`
2. `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile src/yuantus/meta_engine/services/parallel_tasks_service.py src/yuantus/meta_engine/web/parallel_tasks_router.py src/yuantus/meta_engine/services/eco_service.py src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`
   Result: `clean`
3. `git diff --check`
   Result: `clean`

## Outcome

- rule creation now validates `match_predicates`
- runtime evaluation now filters by `workflow_map_id`, `stage_id`, and
  `eco_priority`
- router contract exposes `match_predicates`
- ECO hook context now carries runtime scope needed for stage/priority matching
