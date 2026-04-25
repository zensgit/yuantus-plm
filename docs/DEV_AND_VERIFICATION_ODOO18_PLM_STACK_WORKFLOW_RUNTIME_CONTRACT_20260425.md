# Odoo18 PLM Stack Workflow Runtime Contract - 2026-04-25

## 1. Purpose

The Odoo18 PLM stack has a dedicated manual workflow:

```text
.github/workflows/odoo18-plm-stack-regression.yml
```

Previous guardrails pinned the verifier script, workflow input, and CI
change-scope path. This change pins the workflow runtime assumptions that make
the manual run reproducible: Python version, dependency installation, pycache
location, timeout, permissions, and concurrency.

## 2. Scope

Changed files:

- `.github/workflows/ci.yml`
- `src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_runtime.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, Odoo18 workflow behavior,
router code, schema, or smoke membership was changed.

## 3. Design

The new contract asserts the dedicated workflow keeps these runtime choices:

- `runs-on: ubuntu-latest`
- `timeout-minutes: 30`
- `actions/setup-python@v6`
- Python `3.11`
- pip cache enabled
- `python -m pip install --upgrade pip`
- editable dev install via `pip install -e ".[dev]"`
- `PYTHONPYCACHEPREFIX: /tmp/yuantus-pyc`

It also pins the non-runtime execution safety:

- read-only permissions: `actions: read`, `contents: read`
- serialized concurrency per workflow/ref with `cancel-in-progress: true`

These assertions make the workflow environment explicit without modifying the
workflow itself.

## 4. Contract Tests

Added:

```text
test_odoo18_plm_stack_workflow_runtime_is_pinned_for_reproducibility
test_odoo18_plm_stack_workflow_uses_read_only_permissions_and_serial_concurrency
```

The tests use direct text assertions because the contract is about preserving a
small set of exact workflow declarations.

## 5. Non-Goals

- No change to `.github/workflows/odoo18-plm-stack-regression.yml`.
- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No package dependency changes.
- No new workflow trigger or schedule.
- No production/shared-dev execution.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_runtime.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_runtime.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
git diff --check
bash scripts/verify_odoo18_plm_stack.sh smoke
```

Results:

- workflow runtime contract: 2 passed
- CI wiring/order + Odoo18 contracts: 14 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is a drift guard. If the dedicated workflow later changes runtime versions
or installation strategy, reviewers must update this contract and explain why
the new environment is still compatible with the Odoo18 verification stack.
