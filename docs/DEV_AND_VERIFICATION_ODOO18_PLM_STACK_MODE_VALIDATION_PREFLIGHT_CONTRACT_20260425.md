# Odoo18 PLM Stack Mode Validation Preflight Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` accepts only one optional mode argument:
`smoke` or `full`. Invalid invocation should fail before the verifier performs
repository work such as dynamic router discovery, `py_compile`, or pytest.

This change adds a contract for that preflight order so future edits cannot
accidentally make invalid input run expensive or path-sensitive work.

## 2. Scope

Changed files:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, workflow behavior, router
code, schema, or test membership was changed.

## 3. Design

The verifier already has three validation gates before repository work:

```bash
if [[ "$#" -gt 1 ]]; then
  usage >&2
  exit 2
fi

case "$MODE" in
  -h|--help)
    usage
    exit 0
    ;;
esac

case "$MODE" in
  smoke) ... ;;
  full) ... ;;
  *)
    usage >&2
    exit 2
    ;;
esac

cd "$REPO_ROOT"
```

The contract pins that validation order before `cd "$REPO_ROOT"`, router file
discovery, `py_compile`, and pytest.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_validates_args_and_mode_before_repo_work
```

The test verifies:

- extra positional arguments are rejected before environment/export and repo work
- help handling runs before pycache/export and repo work
- the final mode selection rejects invalid modes before `cd "$REPO_ROOT"`
- router discovery, `py_compile`, and pytest remain after the repo-root change

## 5. Non-Goals

- No change to accepted modes.
- No new CLI flags.
- No change to default `full` behavior.
- No change to test membership.
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

- verifier contract: 14 passed
- CI wiring/order + verifier contract: 16 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is an input-safety guard. If the verifier gains new modes or options, the
new parsing logic should still fail closed before repository work starts.
