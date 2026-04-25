# Odoo18 PLM Stack Dynamic Router Compile Coverage

Date: 2026-04-24

## 1. Purpose

Recent router decomposition work created many split `web/*_router.py` modules.
`scripts/verify_odoo18_plm_stack.sh` had been expanded by hand for some of
those files, but a hand-maintained compile list can drift as new router modules
are added.

This change makes the stack verifier dynamically add every top-level
`src/yuantus/meta_engine/web/*_router.py` file to its `py_compile` gate.

## 2. Scope

Changed:

- `scripts/verify_odoo18_plm_stack.sh`
- `.github/workflows/ci.yml`
- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_DYNAMIC_ROUTER_COMPILE_COVERAGE_20260424.md`

## 3. Design

The verifier still keeps its explicit domain file list. After changing to the
repo root, it appends all top-level web router modules discovered by:

```bash
find "src/yuantus/meta_engine/web" -maxdepth 1 -type f -name "*_router.py" | sort
```

This keeps the smoke script stable for existing domains while making router
syntax coverage automatic for future decomposition increments.

## 4. Contract

A new CI contract asserts:

- dynamic router discovery runs after `cd "$REPO_ROOT"`
- discovered router files are appended to `compile_files`
- discovery happens before the `py_compile` command

The contract test is wired into the CI contracts job.

## 5. Non-Goals

- No runtime router behavior changes.
- No app registration changes.
- No smoke test list expansion.
- No full CI restructuring.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
bash scripts/verify_odoo18_plm_stack.sh smoke
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Results:

- Dynamic router compile contract: `1 passed in 0.01s`
- CI ordering + dynamic router compile contract: `2 passed in 0.02s`
- Doc index contracts: `3 passed in 0.03s`
- Odoo18 PLM stack smoke: `265 passed in 18.53s`
- `bash -n scripts/verify_odoo18_plm_stack.sh`: passed
- `git diff --check`: passed

## 7. Review Notes

Review should focus on whether dynamic compilation is limited enough to avoid
unexpected broadening. The chosen scope is only top-level `web/*_router.py`
modules, not all web helpers or nested GraphQL files.
