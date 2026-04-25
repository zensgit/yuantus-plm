# Odoo18 PLM Stack Compile File Dedup

Date: 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` now dynamically appends every top-level
`src/yuantus/meta_engine/web/*_router.py` file to the py_compile gate. Some
router files are still present in the hand-maintained compile list, so dynamic
discovery can add duplicates.

This change de-duplicates `compile_files` before py_compile runs.

## 2. Scope

Changed:

- `scripts/verify_odoo18_plm_stack.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_COMPILE_FILE_DEDUP_20260425.md`

## 3. Design

The script keeps the explicit domain file list and the dynamic router discovery.
After both sources populate `compile_files`, it builds `deduped_compile_files`
while preserving first-seen order, then assigns the de-duplicated list back to
`compile_files`.

The implementation avoids associative arrays so it remains compatible with the
older Bash available on macOS.

## 4. Contract

The existing dynamic router compile contract now also asserts that de-duplication
happens after router discovery and before the py_compile command.

## 5. Non-Goals

- No runtime router changes.
- No smoke test list changes.
- No removal of hand-maintained compile entries in this increment.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
bash scripts/verify_odoo18_plm_stack.sh smoke
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Results:

- Dynamic router compile contract: `1 passed in 0.01s`
- CI wiring + CI ordering + dynamic router compile contract: `3 passed in 0.02s`
- Doc index contracts: `3 passed in 0.03s`
- Odoo18 PLM stack smoke: `265 passed in 18.40s`
- `bash -n scripts/verify_odoo18_plm_stack.sh`: passed
- `git diff --check`: passed

## 7. Review Notes

Review should confirm the de-duplication remains order-preserving and avoids
Bash associative arrays.
