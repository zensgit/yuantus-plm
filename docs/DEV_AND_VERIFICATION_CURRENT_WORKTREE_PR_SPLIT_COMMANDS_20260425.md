# Current Worktree PR Split Commands - Development And Verification

Date: 2026-04-25

## 1. Goal

Provide a read-only helper for splitting the current large worktree into
reviewable PR groups. The helper prints review and staging command templates
only; it does not run `git add`, commit, push, or modify shared-dev state.

## 2. Design

New helper:

```bash
bash scripts/print_current_worktree_closeout_commands.sh
bash scripts/print_current_worktree_closeout_commands.sh --commands
bash scripts/print_current_worktree_closeout_commands.sh --group closeout-docs-and-index --commands
```

The helper defines four groups:

- `closeout-docs-and-index`: closeout records, delivery index entries, and
  local-only artifact guard.
- `closeout-tooling`: helper script, contract test, CI wiring, and scripts index
  verification.
- `odoo18-verifier-hardening`: Odoo18 PLM stack verifier script, workflow, and
  focused contracts.
- `router-decomposition-portfolio`: router split modules, app registration,
  router tests, and router decomposition records.

The helper explicitly excludes:

- `.claude/`
- `local-dev-env/`

It also supports `--group NAME` for a single review group:

- `closeout-docs-and-index`
- `closeout-tooling`
- `odoo18-verifier-hardening`
- `router-decomposition-portfolio`

## 3. Contract Test

Added:

```text
test_current_worktree_closeout_helper_is_documented_and_prints_expected_groups
```

The test verifies:

- help output documents `--commands`;
- default output prints the four group names;
- command output includes review/staging templates;
- `--group` filters default output to one group;
- `--group ... --commands` filters command output to one group;
- invalid groups fail with exit code 2;
- command output does not include `git add -- .claude` or
  `git add -- local-dev-env`;
- delivery scripts index references the helper.

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
- family-specific router closeout contracts: 51 passed
- odoo18 verifier smoke/full (from this closeout batch): 265/765 passed
- diff whitespace: clean

## 5. Non-Goals

- No automatic staging.
- No commit or push.
- No cleanup of `.claude/` or `local-dev-env/`.
- No change to router behavior.
- No change to Odoo18 verifier behavior.
