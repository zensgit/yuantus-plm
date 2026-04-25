# Odoo18 PLM Stack Extra Args Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` accepts one optional mode argument:
`smoke` or `full`. Before this change, extra positional arguments were silently
ignored because the script only read `$1`.

That is unsafe for a verification entrypoint. A mistyped command such as
`scripts/verify_odoo18_plm_stack.sh smoke typo` looked successful while not
doing what the caller intended.

## 2. Scope

Changed files:

- `scripts/verify_odoo18_plm_stack.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, router code, schema, fixture, or CI workflow was
changed.

## 3. Design

The script now rejects more than one positional argument before dispatching the
mode:

```bash
if [[ "$#" -gt 1 ]]; then
  usage >&2
  exit 2
fi
```

This preserves the existing public contract:

- no argument defaults to `full`
- `smoke` runs the focused smoke set
- `full` runs the broader regression set
- `--help` prints usage and exits 0
- invalid mode exits 2 without running py_compile or pytest

The new behavior is only for extra arguments: any invocation with two or more
positional arguments exits 2, prints usage on stderr, and does not emit
`[verify_odoo18_plm_stack]` progress markers.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_rejects_extra_args_without_running
```

The test executes:

```bash
bash scripts/verify_odoo18_plm_stack.sh smoke extra
```

Expected behavior:

- return code is `2`
- stdout is empty
- stderr contains the script usage
- stderr does not contain `[verify_odoo18_plm_stack]`

This pins the failure before any compile or pytest work starts.

## 5. Compatibility

Existing references were checked before the change. The repository only uses
zero-argument, `smoke`, `full`, or single CI-mode invocations for
`verify_odoo18_plm_stack.sh`.

No known valid caller depends on extra positional arguments.

## 6. Non-Goals

- No new script options or flags.
- No change to `smoke` or `full` test membership.
- No change to dynamic router compile discovery.
- No change to CI workflow wiring.
- No change to app/router behavior.

## 7. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
bash scripts/verify_odoo18_plm_stack.sh smoke
```

Results:

- Odoo18 stack contract: 6 passed
- CI wiring/order contract: 8 passed
- doc index contracts: 3 passed
- shell syntax: passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 8. Review Notes

This is a fail-fast guard for the verification script itself. It intentionally
does not broaden the script CLI; it narrows accepted input so incorrect
automation cannot be masked by a green run.
