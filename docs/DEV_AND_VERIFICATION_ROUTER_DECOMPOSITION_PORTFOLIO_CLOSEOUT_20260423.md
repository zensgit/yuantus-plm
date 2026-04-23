# Router Decomposition Portfolio Closeout

Date: 2026-04-23

## 1. Scope

This closeout records a portfolio-level guard for completed router decomposition lines.

It covers:

- BOM router decomposition.
- CAD router decomposition.
- File router decomposition.
- ECO router decomposition.
- Parallel tasks router decomposition.

This is a test and documentation increment only. It does not move routes, change runtime behavior, alter auth, mutate shared-dev `142`, or enable scheduler work.

## 2. Reason

The decomposed router families do not all have the same legacy-shell state:

| Family | Legacy module | Intended state |
| --- | --- | --- |
| BOM | `bom_router.py` | registered empty compatibility shell |
| CAD | `cad_router.py` | registered empty compatibility shell |
| File | `file_router.py` | unregistered empty compatibility shell |
| ECO | `eco_router.py` | unregistered compatibility shim to `eco_core_router` |
| Parallel tasks | `parallel_tasks_router.py` | unregistered empty compatibility shell |

Those differences are intentional. The new portfolio contract prevents accidental drift, such as adding a handler back into a legacy shell or re-registering an unregistered shell in `create_app()`.

## 3. Implementation

Added:

- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`

The contract asserts:

- The five legacy aggregate router modules declare no route decorators.
- BOM and CAD legacy shells remain registered because that is their current compatibility contract.
- File, ECO, and parallel tasks legacy shells remain unregistered in `app.py`.
- No FastAPI route endpoint is owned by a legacy aggregate module.
- CI contracts job includes the portfolio contract and the key per-family router decomposition contracts.

Updated:

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_file_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_legacy_router_contracts.py
```

Result: `23 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_*_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_*_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_*_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_*_router_contracts.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_*_router_contracts.py
```

Result: `181 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `4 passed`.

```bash
git diff --check
```

Result: passed.

## 5. Non-Goals

- No route relocation.
- No public API changes.
- No router shell deletion.
- No scheduler enablement.
- No shared-dev `142` operation.
- No UI work.

## 6. Closeout Status

The portfolio closeout is complete. The new contract, CI registration, doc index registration, focused verification, and wider router decomposition contract sweep all pass locally.
