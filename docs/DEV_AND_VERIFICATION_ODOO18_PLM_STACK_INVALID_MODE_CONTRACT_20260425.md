# Odoo18 PLM Stack Invalid Mode Contract

Date: 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` is a verification entrypoint with two valid
modes: `smoke` and `full`. Invalid arguments should fail before py_compile or
pytest execution starts.

This change adds a contract for that failure behavior.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_INVALID_MODE_CONTRACT_20260425.md`

## 3. Design

No runtime script logic changed in this increment. The previous help contract
already made invalid modes reuse the shared `usage()` helper and exit `2`.

This increment pins that behavior so future refactors cannot accidentally run
the smoke path for an invalid mode.

## 4. Contract

The contract runs:

```bash
bash scripts/verify_odoo18_plm_stack.sh invalid-mode
```

It asserts:

- exit code is `2`
- stdout is empty
- stderr contains usage text
- stderr does not contain `[verify_odoo18_plm_stack]` execution logs

## 5. Non-Goals

- No changes to `smoke` or `full` behavior.
- No changes to help text semantics.
- No script list changes.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
bash scripts/verify_odoo18_plm_stack.sh smoke
git diff --check
```

Results:

- Odoo18 PLM stack contract: `3 passed in 0.03s`
- CI wiring + CI ordering + Odoo18 PLM stack contract: `5 passed in 0.04s`
- Doc index contracts: `3 passed in 0.03s`
- Odoo18 PLM stack smoke: `265 passed in 18.58s`
- `git diff --check`: passed

## 7. Review Notes

Review should confirm the invalid-mode contract checks the no-run behavior, not
just the exit code.
