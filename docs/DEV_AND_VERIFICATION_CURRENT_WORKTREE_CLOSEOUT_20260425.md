# Current Worktree Closeout - Development And Verification

Date: 2026-04-25

## 1. Goal

Close the current development batch into auditable groups before opening another
feature cycle. The worktree contains several completed router decomposition
families, Odoo18 PLM stack verifier hardening, and delivery index updates.

This closeout is documentation-only. It does not change runtime behavior,
schema, router ownership, workflow behavior, or shared-dev state.

## 2. Worktree Groups

| Group | Contents | Handling |
| --- | --- | --- |
| Router decomposition closeouts | approvals, box, cutted parts, document sync, maintenance, quality, report, subcontracting, version router files and contracts | Keep as implementation/review batch; do not mix with new features |
| Odoo18 verifier hardening | `scripts/verify_odoo18_plm_stack.sh`, Odoo18 workflow contracts, shell syntax, dynamic router compile, CLI safety contracts | Close with a single verifier hardening summary |
| Delivery documentation indexes | `docs/DELIVERY_DOC_INDEX.md`, `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`, DEV_AND_VERIFICATION records | Keep index entries sorted and covered by contracts |
| Local-only state | `.claude/`, `local-dev-env/` | Do not commit |

## 3. Current Status Snapshot

`git status --short` shows modified tracked files in CI, docs, verifier script,
router tests, router modules, and app registration. It also shows many
untracked DEV_AND_VERIFICATION records, router contract tests, split router
modules, `.claude/`, and `local-dev-env/`.

The closeout boundary is:

- commit or PR only coherent groups;
- keep `.claude/` and `local-dev-env/` local;
- do not start scheduler production, shared-dev writes, UI, or new product
  features from this batch;
- treat any new feature as a new cycle with a taskbook.

## 4. Verification Plan

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

## 5. Non-Goals

- No commit or push.
- No cleanup of unrelated dirty files.
- No deletion of compatibility shells.
- No shared-dev `142` bootstrap or write operation.
- No scheduler production enablement.
- No UI or product feature implementation.

## 6. Handoff Notes

The next implementation should not continue adding verifier micro-contracts by
default. The safe next step is a review/PR split by the groups above, then a new
cycle only after a bounded target is selected.
