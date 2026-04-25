# Odoo18 PLM Stack Verifier Hardening Closeout - 2026-04-25

## 1. Goal

Close the Odoo18 PLM stack verifier hardening line as a coherent validation
surface. The verifier is now guarded by discoverability, shell syntax, workflow,
CLI safety, execution order, interpreter, pycache, dynamic router compile, and
change-scope contracts.

This closeout is documentation-only. It does not change
`scripts/verify_odoo18_plm_stack.sh`, CI workflow behavior, test membership, or
runtime application code.

## 2. Hardened Contract Surface

| Area | Contract |
| --- | --- |
| Script discoverability | verifier script is present and indexed |
| Shell syntax | verifier is covered by shell syntax checks |
| Dynamic router compile coverage | all top-level `*_router.py` files are discovered and compiled |
| Compile list dedup | manual and dynamic compile entries are deduplicated before `py_compile` |
| Help and invalid input | `--help`, invalid mode, and extra args exit without running verifier work |
| Default mode | no argument defaults to `full` |
| Interpreter selection | `PY_BIN` prefers repo `.venv/bin/python`, pytest defaults to `PY_BIN -m pytest` |
| Pycache isolation | `PYTHONPYCACHEPREFIX` is exported before Python work |
| Repo root anchor | repo-relative paths run after `cd "$REPO_ROOT"` |
| Mode validation preflight | argument and mode validation happen before repo work |
| Phase order | mode marker, compile, pytest, and `PASS` stay ordered |
| Workflow input/runtime/change scope | workflow mode input, runtime setup, and CI change detection are pinned |

## 3. Public Interface

The public verifier interface remains:

```bash
scripts/verify_odoo18_plm_stack.sh [smoke|full]
```

Environment controls remain:

- `PY_BIN`
- `PYTEST_BIN`
- `PYTHONPYCACHEPREFIX`

No new flags, modes, workflow inputs, or output formats were introduced.

## 4. Stop Point

Do not continue adding one-off verifier micro-contracts unless a concrete defect
is found. Future verifier work should be one of:

- fixing a real broken contract;
- updating contracts after an intentional interface change;
- expanding test membership for a named Odoo18 PLM domain.

## 5. Verification Plan

Commands:

```bash
git diff --check

bash -n scripts/verify_odoo18_plm_stack.sh

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_runtime.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash scripts/verify_odoo18_plm_stack.sh smoke
bash scripts/verify_odoo18_plm_stack.sh full
```

Results:

- diff whitespace: clean
- shell syntax: passed
- shell syntax pytest: 18 passed
- Odoo18 verifier focused contracts: 21 passed
- CI wiring/order contracts: 2 passed
- doc index contracts: 3 passed
- Odoo18 smoke: 265 passed
- Odoo18 full: 765 passed

## 6. Non-Goals

- No change to verifier behavior.
- No new Odoo18 workflow mode.
- No shared-dev `142` execution.
- No new router decomposition work.
- No scheduler production enablement.
