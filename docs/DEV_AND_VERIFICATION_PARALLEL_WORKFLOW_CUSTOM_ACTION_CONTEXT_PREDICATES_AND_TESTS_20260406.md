# Verification: Workflow Custom Action Context Predicates and Tests

## Date

2026-04-06

## Scope

Verified white-listed context predicate support for workflow custom actions:

- `actor_roles`
- `product_id`
- `eco_type`

## Commands

1. `pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py -k 'workflow or custom_action or trigger_phase or set_eco_priority'`
   Result: `14 passed, 178 deselected`
2. `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile src/yuantus/meta_engine/services/parallel_tasks_service.py src/yuantus/meta_engine/web/parallel_tasks_router.py src/yuantus/meta_engine/services/eco_service.py src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`
   Result: `clean`
3. `git diff --check`
   Result: `clean`

## Outcome

- rule validation now accepts only the expanded allowlist of context predicates
- runtime matching now filters by `actor_roles`, `product_id`, and `eco_type`
- manual execute injects current-user roles into context
- ECO hooks now provide actor/product/type context needed by role- and
  product-scoped rules
