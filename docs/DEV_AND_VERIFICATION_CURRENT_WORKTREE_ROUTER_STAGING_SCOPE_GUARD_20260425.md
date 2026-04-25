# Current Worktree Router Staging Scope Guard - Development And Verification

Date: 2026-04-25

## 1. Goal

Narrow the `router-decomposition-portfolio` staging template emitted by
`scripts/print_current_worktree_closeout_commands.sh`. The previous template
used broad directories such as `src/yuantus/meta_engine/web` and
`src/yuantus/meta_engine/tests`, which could accidentally stage Odoo18 verifier,
doc-index, or other non-router follow-up files.

This change keeps the helper read-only. It only changes printed review/staging
templates and their contract test.

## 2. Design

The router portfolio command now prints explicit router-family pathspecs:

- web router families: approval, box, cutted parts, document sync, maintenance,
  quality, report, subcontracting, and version;
- router contract test families matching those routers;
- `quality_common.py` and `test_router_decomposition_portfolio_contracts.py`;
- router decomposition DEV_AND_VERIFICATION documents and the report router
  taskbook.

The command intentionally does not print broad staging forms:

```bash
git add -- src/yuantus/api/app.py src/yuantus/meta_engine/web ...
git add -- ... src/yuantus/meta_engine/tests ...
```

## 3. Contract Test

Updated:

```text
test_current_worktree_closeout_helper_is_documented_and_prints_expected_groups
```

The test now asserts:

- router group command output contains narrow web/test pathspecs;
- `quality_common.py` is included;
- portfolio contract tests are included;
- broad web/test directory staging does not appear.

## 4. Verification

Commands:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_current_worktree_closeout_commands.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

Results:

- current worktree helper contract: 1 passed
- delivery scripts index contract: 2 passed
- shell syntax pytest: 18 passed
- CI wiring/order contracts: 2 passed
- doc index contracts: 4 passed
- diff whitespace: clean

## 5. Non-Goals

- No automatic staging.
- No commit or push.
- No change to router behavior.
- No change to Odoo18 verifier behavior.
- No cleanup of existing dirty worktree files.
