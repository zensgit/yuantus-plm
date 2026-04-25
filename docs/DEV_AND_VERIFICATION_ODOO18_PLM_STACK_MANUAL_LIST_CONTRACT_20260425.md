# Odoo18 PLM Stack Manual List Contract

Date: 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` contains three curated shell arrays:

- `compile_files`
- `smoke_tests`
- `full_tests`

Those lists are intentionally hand-maintained because they define a focused
Odoo18 PLM verification surface. Without a contract, stale paths or accidental
duplicates can make the script fail late or silently drift.

This change adds contracts for those manual lists.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_MANUAL_LIST_CONTRACT_20260425.md`

## 3. Design

The test parses the script's shell arrays directly and asserts:

- each manual list exists
- each list is non-empty
- each list has no duplicate entries
- each path exists in the repository
- `smoke_tests` is a subset of `full_tests`

The dynamic router discovery path remains separately covered by the dynamic
router compile contract.

## 4. Non-Goals

- No changes to the script's selected test lists.
- No changes to smoke or full behavior.
- No attempt to make all script lists dynamic.

## 5. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
bash scripts/verify_odoo18_plm_stack.sh smoke
git diff --check
```

Results:

- Odoo18 PLM stack contract: `5 passed in 0.04s`
- CI wiring + CI ordering + Odoo18 PLM stack contract: `7 passed in 0.04s`
- Doc index contracts: `3 passed in 0.03s`
- Odoo18 PLM stack smoke: `265 passed in 18.15s`
- `git diff --check`: passed

## 6. Review Notes

Review should confirm this contract protects only the intentional manual lists
and does not attempt to parse generated dynamic router additions.
