# Odoo18 PLM Stack Repo Root Anchor Contract - 2026-04-25

## 1. Purpose

`scripts/verify_odoo18_plm_stack.sh` uses repository-relative paths for router
discovery, `py_compile`, and pytest. The verifier must therefore anchor itself
to the repository root before doing any path-sensitive work.

This change adds a contract so the script remains safe to invoke from CI,
developer shells, or wrapper scripts whose current working directory is not the
repo root.

## 2. Scope

Changed files:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py`
- `docs/DELIVERY_DOC_INDEX.md`

No runtime application code, verifier script behavior, workflow behavior, router
code, schema, or test membership was changed.

## 3. Design

The script already derives root paths from its own location:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
...
cd "$REPO_ROOT"
```

The contract pins the ordering that matters:

1. read mode
2. derive `SCRIPT_DIR`
3. derive `REPO_ROOT`
4. `cd "$REPO_ROOT"`
5. discover router files
6. run `py_compile`
7. run pytest

This keeps all relative paths resolved from the same repository root.

## 4. Contract Test

Added:

```text
test_odoo18_plm_stack_verifier_anchors_execution_to_repo_root_before_work
```

The test verifies that `SCRIPT_DIR` and `REPO_ROOT` are computed before the
script changes directory, and that `cd "$REPO_ROOT"` runs before dynamic router
discovery, `py_compile`, and pytest.

## 5. Non-Goals

- No change to `scripts/verify_odoo18_plm_stack.sh`.
- No new command-line option.
- No change to smoke/full test membership.
- No change to CI workflow inputs.
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

- verifier contract: 13 passed
- CI wiring/order + verifier contract: 15 passed
- doc index contracts: 3 passed
- diff whitespace: clean
- Odoo18 smoke: 265 passed

## 7. Review Notes

This is a portability guard. If the verifier is later made callable from another
location or wrapped by another script, repository-relative file lists and dynamic
router discovery must still execute after the root anchor is established.
