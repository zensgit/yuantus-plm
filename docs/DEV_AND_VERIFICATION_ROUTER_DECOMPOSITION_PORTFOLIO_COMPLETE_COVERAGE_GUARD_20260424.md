# Router Decomposition Portfolio Complete Coverage Guard

Date: 2026-04-24

## 1. Purpose

The router decomposition portfolio had reached a manually verified `80/80/80`
state:

- 80 router contract files on disk
- 80 entries in `CI_PORTFOLIO_ENTRIES`
- 80 contract files wired into the CI contracts job

This change converts that manual equality check into a permanent test contract.
Future router decomposition work must now update the portfolio list whenever it
adds a new `test_*router*_contracts.py` file.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ROUTER_DECOMPOSITION_PORTFOLIO_COMPLETE_COVERAGE_GUARD_20260424.md`

The new test walks `src/yuantus/meta_engine/tests/test_*router*_contracts.py`
from disk and compares it exactly with `CI_PORTFOLIO_ENTRIES`.

## 3. Design

The guard is intentionally placed in the existing portfolio contract file rather
than in CI YAML parsing logic. The portfolio contract is the authoritative
closeout point for router decomposition, so it should fail first when the
portfolio surface is incomplete.

The check is bidirectional:

- A contract file on disk but missing from `CI_PORTFOLIO_ENTRIES` fails.
- A stale `CI_PORTFOLIO_ENTRIES` value without a matching file on disk fails.

The existing CI test still verifies that every portfolio entry is present in
`.github/workflows/ci.yml`.

## 4. Non-Goals

- No runtime router changes.
- No route registration changes.
- No CI job restructuring.
- No changes to split router ownership contracts.

## 5. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_*router*_contracts.py
bash scripts/verify_odoo18_plm_stack.sh smoke
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Results:

- Portfolio contract: `5 passed in 1.79s`
- Portfolio + CI ordering: `6 passed in 1.79s`
- Doc index contracts: `3 passed in 0.03s`
- Full router contract sweep: `401 passed in 65.27s`
- Odoo18 PLM stack smoke: `265 passed in 19.14s`
- `bash -n scripts/verify_odoo18_plm_stack.sh`: passed
- `git diff --check`: passed

## 6. Review Notes

Review should focus on whether the glob pattern matches the intended portfolio
surface and whether the equality assertion is stricter than the previous
one-way CI inclusion check.
