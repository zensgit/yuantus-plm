# Odoo18 PLM Stack Default Mode Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` accepts one optional mode argument. When no
mode is provided, the script should run the broader `full` suite, not the
lighter `smoke` suite.

The current behavior is:

```bash
MODE="${1:-full}"
```

This change adds a contract so the no-argument default cannot drift silently.

## 2. Scope

Changed files:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, workflow behavior, router
code, schema, or test membership was changed.

## 3. Design

The contract asserts:

- `MODE` defaults to `full` when `$1` is absent
- help text documents `full` as the default
- the `full_tests` array exists before mode dispatch
- the `full)` case maps to `selected_tests=("${full_tests[@]}")`
- invalid modes still fall through to usage + exit 2

The test is static by design. It verifies the default-mode contract without
running the full Odoo18 suite during the contracts job.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_defaults_no_arg_to_full_mode
```

This complements the existing runtime-ish contracts for help, invalid mode, and
extra args.

## 5. Non-Goals

- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No change to `smoke` or `full` test lists.
- No execution of the full suite in this contract.
- No workflow change.
- No production/shared-dev execution.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
git diff --check
bash scripts/verify_odoo18_plm_stack.sh smoke
```

Results:

- verifier contract: 11 passed
- CI wiring/order + verifier contract: 13 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is a default-safety guard. If the no-argument default changes from `full`,
the review should explicitly justify why a lighter default is acceptable for the
Odoo18 verification entrypoint.
