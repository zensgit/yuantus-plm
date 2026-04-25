# Cutted Parts Router Decomposition R1 - Throughput And Bottlenecks

Date: 2026-04-24

## Scope

This increment mechanically moves the C43 throughput/cadence endpoints and the
C46 saturation/bottleneck endpoints out of `cutted_parts_router.py`.

Moved public routes:

- `GET /api/v1/cutted-parts/throughput/overview`
- `GET /api/v1/cutted-parts/cadence/summary`
- `GET /api/v1/cutted-parts/plans/{plan_id}/cadence`
- `GET /api/v1/cutted-parts/export/cadence`
- `GET /api/v1/cutted-parts/saturation/overview`
- `GET /api/v1/cutted-parts/bottlenecks/summary`
- `GET /api/v1/cutted-parts/plans/{plan_id}/bottlenecks`
- `GET /api/v1/cutted-parts/export/bottlenecks`

## Design

Two focused routers were introduced:

- `cutted_parts_throughput_router.py` owns C43 throughput/cadence reads.
- `cutted_parts_bottlenecks_router.py` owns C46 saturation/bottleneck reads.

Both routers keep the existing prefix `/cutted-parts` and tag `Cutted Parts`.
The handler bodies are a mechanical relocation of the existing service calls;
the two plan-specific routes preserve the existing `ValueError -> 404` mapping.

`create_app()` now registers the split routers before the legacy
`cutted_parts_router`, so route ownership is deterministic while the remaining
36 cutted-parts endpoints stay in the legacy router for later slices.

## Files

- `src/yuantus/meta_engine/web/cutted_parts_throughput_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_bottlenecks_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_r1_contracts.py`
- `.github/workflows/ci.yml`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/DELIVERY_DOC_INDEX.md`

## Contracts

`test_cutted_parts_router_decomposition_r1_contracts.py` pins:

- The 8 moved route `(method, path)` pairs resolve to the expected split router modules.
- The moved decorators are absent from `cutted_parts_router.py`.
- `app.py` registers throughput router, bottleneck router, then legacy router.
- Every moved route is registered exactly once.
- The public `Cutted Parts` tag is preserved.

The contract is wired into the CI contracts job and the router decomposition
portfolio surface.

## Verification

Commands executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/web/cutted_parts_throughput_router.py \
  src/yuantus/meta_engine/web/cutted_parts_bottlenecks_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_r1_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -m pytest -q $(rg --files src/yuantus/meta_engine/tests | rg 'router.*contracts\.py$|legacy_router_contracts\.py$')

git diff --check
```

Result:

- `py_compile` passed.
- Focused cutted-parts/router contract regression: `68 passed in 3.84s`.
- Doc index and CI list contracts: `4 passed in 0.03s`.
- Router contract sweep: `338 passed in 52.25s`.
- `git diff --check` passed.

## Non-Goals

- No service behavior changes.
- No schema or migration changes.
- No cutted-parts write-path movement.
- No closeout shell conversion for `cutted_parts_router.py`; the legacy router
  intentionally kept the remaining endpoints at the R1 boundary. This was
  superseded by
  `DEV_AND_VERIFICATION_CUTTED_PARTS_ROUTER_DECOMPOSITION_CLOSEOUT_20260424.md`.
