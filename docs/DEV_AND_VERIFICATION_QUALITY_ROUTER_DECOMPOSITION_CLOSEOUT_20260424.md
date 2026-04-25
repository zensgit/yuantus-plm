# Quality Router Decomposition Closeout

Date: 2026-04-24

## 1. Scope

This change decomposes the core Quality router into three focused routers and
turns the legacy `quality_router.py` into an empty compatibility shell.

Moved route families:

- Quality points: `quality_points_router.py`
- Quality checks: `quality_checks_router.py`
- Quality alerts: `quality_alerts_router.py`

The existing `quality_analytics_router.py` remains unchanged because it was
already split from the core quality router.

## 2. Final Route Ownership

Core `/api/v1/quality/*` ownership after closeout:

- `quality_points_router`: `/points`, `/points/{point_id}`
- `quality_checks_router`: `/checks`, `/checks/{check_id}`, `/checks/{check_id}/record`
- `quality_alerts_router`: `/alerts`, `/alerts/{alert_id}`, `/alerts/{alert_id}/transition`, `/alerts/{alert_id}/manufacturing-context`
- `quality_router`: empty compatibility shell only
- `quality_analytics_router`: unchanged analytics and SPC endpoints

Registration order in `app.py`:

1. `quality_points_router`
2. `quality_checks_router`
3. `quality_alerts_router`
4. `quality_router`
5. `quality_analytics_router`

## 3. Design

Shared request models and serializers moved to `quality_common.py` so the split
routers do not import from the legacy shell. This keeps `quality_router.py`
route-free and avoids circular imports.

No service behavior changed. Each split router still constructs `QualityService`
directly, maps `ValueError` to the same HTTP status, and returns the same
serializer output as before.

## 4. Runtime Changes

- Added `src/yuantus/meta_engine/web/quality_common.py`.
- Added `src/yuantus/meta_engine/web/quality_points_router.py`.
- Added `src/yuantus/meta_engine/web/quality_checks_router.py`.
- Added `src/yuantus/meta_engine/web/quality_alerts_router.py`.
- Converted `src/yuantus/meta_engine/web/quality_router.py` to a legacy shell.
- Registered split routers in `src/yuantus/api/app.py`.
- Updated `test_quality_router.py` patch targets and isolated router setup.
- Added `test_quality_router_decomposition_closeout_contracts.py`.
- Added Quality to the router decomposition portfolio contract.

## 5. Contracts

The closeout contract asserts:

- legacy `quality_router.py` declares no route decorators;
- every core Quality route is owned by the expected split router;
- every moved route is registered exactly once;
- split routers are registered before the legacy shell;
- all moved routes keep the `Quality` tag.

The new contract is registered in `.github/workflows/ci.yml`.

## 6. Verification

Py compile:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/quality_common.py \
  src/yuantus/meta_engine/web/quality_points_router.py \
  src/yuantus/meta_engine/web/quality_checks_router.py \
  src/yuantus/meta_engine/web/quality_alerts_router.py \
  src/yuantus/meta_engine/web/quality_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Focused Quality regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_quality_router.py \
  src/yuantus/meta_engine/tests/test_quality_analytics_router.py \
  src/yuantus/meta_engine/tests/test_quality_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py
```

Result: `28 passed in 3.50s`.

Full router contract sweep:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_*router*_contracts.py
```

Result: `333 passed in 50.47s`.

Doc index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `3 passed in 0.02s`.

Diff whitespace check:

```bash
git diff --check
```

Result: passed.

## 7. Explicit Non-Goals

- Do not change `QualityService`.
- Do not change analytics/SPC routes.
- Do not change auth semantics.
- Do not change response payloads.
- Do not remove the legacy `quality_router` import surface.

## 8. Next Candidate

The next high-ROI router decomposition candidate is `cutted_parts_router.py`,
starting with the throughput/cadence and saturation/bottlenecks route groups.
