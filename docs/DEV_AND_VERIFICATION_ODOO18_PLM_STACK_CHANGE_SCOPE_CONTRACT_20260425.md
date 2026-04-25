# Odoo18 PLM Stack Change Scope Contract - 2026-04-25

## 1. Purpose

The Odoo18 PLM verification path now has script-level contracts and a dedicated
workflow input contract. This change pins the CI change-scope behavior that
makes those contracts run when either the verifier script or the dedicated
workflow changes.

Without this guard, a future edit could accidentally narrow `detect_changes`
and let Odoo18 verification entrypoint changes skip the contracts job.

## 2. Scope

Changed files:

- `.github/workflows/ci.yml`
- `src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, Odoo18 workflow behavior,
router code, schema, or smoke membership was changed.

## 3. Design

The new contract checks two things:

1. CI change detection still sets `run_contracts=true` for workflow changes:

```text
.github/workflows/*.yml|.github/workflows/*.yaml
```

2. CI change detection still sets `run_contracts=true` for script changes:

```text
scripts/*.sh|scripts/*.py
```

That covers the two Odoo18 entrypoint files:

- `.github/workflows/odoo18-plm-stack-regression.yml`
- `scripts/verify_odoo18_plm_stack.sh`

The contract also asserts the Odoo18-specific contract tests are wired into the
CI `contracts` job:

- `test_ci_contracts_odoo18_plm_stack_change_scope.py`
- `test_ci_contracts_odoo18_plm_stack_workflow_input.py`
- `test_ci_contracts_verify_odoo18_plm_stack_discoverability.py`
- `test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`

## 4. Contract Tests

Added:

```text
test_odoo18_plm_stack_workflow_and_script_changes_trigger_contracts
test_odoo18_plm_stack_contract_tests_are_in_ci_contracts_job
```

The tests are text-level by design. This keeps them fast and focused on the CI
configuration surface that controls whether the contract job runs.

## 5. Non-Goals

- No change to CI change-scope implementation.
- No change to `.github/workflows/odoo18-plm-stack-regression.yml`.
- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No new workflow trigger or schedule.
- No production/shared-dev execution.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
git diff --check
bash scripts/verify_odoo18_plm_stack.sh smoke
```

Results:

- change-scope contract: 2 passed
- CI wiring/order + Odoo18 contracts: 12 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is an execution-surface guard, not a behavior change. It makes the Odoo18
verification contracts self-protecting: changes to either the script entrypoint
or the workflow entrypoint must keep the contracts job active.
