# Dev & Verification: Parallel P3 Checkout Gate + Breakage Dimensions + BOM Compare Mode

Date: 2026-03-06

## Scope

Implemented and validated three parallel branches:

1. Checkout gate threshold/policy controls (`doc_sync_*` knobs)
2. Breakage grouped dimensions extension (`mbom_id`, `routing_id`)
3. BOM compare mode extension (`by_item`)

## Code Changes

- Checkout gate policy/threshold support:
  - `src/yuantus/meta_engine/services/parallel_tasks_service.py`
  - `src/yuantus/meta_engine/web/version_router.py`
  - `src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py`
  - `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- Breakage dimension aggregates/groups/cockpit + router descriptions:
  - `src/yuantus/meta_engine/services/parallel_tasks_service.py`
  - `src/yuantus/meta_engine/web/parallel_tasks_router.py`
  - `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
  - `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- BOM compare mode (`by_item`) + descriptions + tests:
  - `src/yuantus/meta_engine/services/bom_service.py`
  - `src/yuantus/meta_engine/web/bom_router.py`
  - `src/yuantus/meta_engine/web/eco_router.py`
  - `src/yuantus/meta_engine/tests/test_plugin_bom_compare.py`

## Validation Commands and Results

### Targeted suites

```bash
pytest -q src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py
```

Result: `5 passed`

```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_bom_compare.py
```

Result: `10 passed, 1 skipped`

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py
```

Result: `55 passed`

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py
```

Result: `114 passed`

### Full strict gate

```bash
bash scripts/strict_gate.sh
```

Result:

- non-DB: `237 passed`
- DB: `603 passed`
- Playwright: `21 passed, 1 skipped`
- Final: `STRICT_GATE: PASS`

## Notes

- Existing environment warnings remain non-blocking (starlette/httpx deprecations, legacy bootstrap deprecation warning); no new blocker introduced by this iteration.
- All added API fields are additive and backward compatible.
