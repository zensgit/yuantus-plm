# Odoo18 PLM Stack Strict Bash Mode Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` is a verification entrypoint. It must fail
fast when commands fail, variables are undefined, or pipelines contain a failing
command.

The script already starts with:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

This change adds a contract so the strict mode cannot be removed silently.

## 2. Scope

Changed files:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, workflow behavior, router
code, schema, or smoke membership was changed.

## 3. Design

The contract asserts the first two lines of the verifier script are exactly:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

This keeps the shell execution policy visible and stable:

- `-e`: stop on command failure
- `-u`: stop on undefined variables
- `-o pipefail`: stop when any command in a pipeline fails

The test is intentionally static because the goal is to prevent structural drift
in the script header.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_uses_strict_bash_mode
```

The test reads `scripts/verify_odoo18_plm_stack.sh` and pins the shebang plus
strict mode line.

## 5. Non-Goals

- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No change to workflow behavior.
- No change to `smoke` or `full` test lists.
- No shell lint dependency.
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

- verifier contract: 9 passed
- CI wiring/order + verifier contract: 11 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is a fail-fast guard. If strict mode is ever relaxed, reviewers should
require a concrete reason and a replacement failure-detection mechanism.
