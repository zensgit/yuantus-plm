# Odoo18 PLM Stack Workflow Input Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` now rejects invalid modes and extra
positional arguments. The GitHub workflow that calls it should also expose a
narrow input surface so manual CI runs cannot accidentally pass an unsupported
mode or append extra arguments.

This change adds a CI contract for `.github/workflows/odoo18-plm-stack-regression.yml`.

## 2. Scope

Changed files:

- `.github/workflows/ci.yml`
- `src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, router code, smoke membership, or Odoo18 verifier
script behavior was changed.

## 3. Design

The contract pins two workflow properties:

1. `workflow_dispatch.inputs.mode` is a `choice` input with only `smoke` and
   `full`, defaulting to `full`.
2. The workflow invokes `scripts/verify_odoo18_plm_stack.sh` exactly once with
   one argument:

```bash
scripts/verify_odoo18_plm_stack.sh "${{ github.event.inputs.mode || 'full' }}"
```

This pairs with the script-level fail-fast guard. The UI layer is constrained to
valid modes, and the script still rejects invalid direct CLI usage.

## 4. Contract Tests

Added:

```text
test_odoo18_plm_stack_workflow_mode_input_is_choice_limited
test_odoo18_plm_stack_workflow_invokes_verifier_with_single_mode_arg
```

The tests intentionally use text-level assertions rather than rewriting the
workflow parser. The contract is about preserving the exact operator-facing
input and shell invocation.

## 5. Non-Goals

- No change to `.github/workflows/odoo18-plm-stack-regression.yml`.
- No new workflow inputs.
- No schedule trigger.
- No production/shared-dev execution.
- No change to the `smoke` or `full` test lists.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
git diff --check
bash scripts/verify_odoo18_plm_stack.sh smoke
```

Results:

- workflow input contract: 2 passed
- CI wiring/order + Odoo18 contracts: 10 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is a CI guard only. It makes the dedicated Odoo18 workflow fail the
contracts if someone changes the manual input to a free-form string, adds
unexpected options, or changes the run step to pass more than one positional
argument.
