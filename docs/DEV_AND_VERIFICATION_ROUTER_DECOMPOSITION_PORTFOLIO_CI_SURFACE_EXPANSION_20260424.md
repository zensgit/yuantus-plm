# DEV AND VERIFICATION - Router Decomposition Portfolio CI Surface Expansion

Date: 2026-04-24

## 1. Scope

The CI contracts job already runs every router decomposition contract, but the
global portfolio contract only required a subset of those files to remain wired
into CI. This increment expands `CI_PORTFOLIO_ENTRIES` so ECO, File, and
Parallel Tasks split-router contracts are also enforced by the portfolio gate.

## 2. Design

`test_router_decomposition_portfolio_contracts.py` contains
`CI_PORTFOLIO_ENTRIES`, a curated list of router-decomposition contract tests
that must remain in `.github/workflows/ci.yml`.

This change adds the contract files that were already present in CI but not
yet present in the portfolio list:

- ECO split contracts: approval ops, approval workflow, change analysis, core,
  impact/apply, lifecycle, and stage routers.
- File split contracts: attachment, conversion, metadata, shell, storage, and
  viewer routers.
- Parallel Tasks split contracts: breakage, CAD 3D, consumption, document sync,
  ECO activities, ops, workflow actions, and workorder docs routers.

No runtime imports, route ownership, app registration, or router implementation
changed.

## 3. Files Changed

- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ROUTER_DECOMPOSITION_PORTFOLIO_CI_SURFACE_EXPANSION_20260424.md`

## 4. Contracts

The portfolio contract now fails if any of the added ECO, File, or Parallel
Tasks split-router contract files are removed from the CI contracts job.

This closes the gap between "CI runs these contract tests today" and "the
portfolio gate ensures CI continues to run them tomorrow."

## 5. Non-Goals

- No runtime code changes.
- No route movement.
- No app registration changes.
- No changes to the CI workflow itself; the files were already listed there.
- No new router decomposition slice.

## 6. Verification

Completed locally:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py
```

Result: 4 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

Result: 5 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: 3 passed.

```bash
bash scripts/verify_odoo18_plm_stack.sh smoke
```

Result: 265 passed.

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_*router*_contracts.py
```

Result: 400 passed.

```bash
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Result: passed.
