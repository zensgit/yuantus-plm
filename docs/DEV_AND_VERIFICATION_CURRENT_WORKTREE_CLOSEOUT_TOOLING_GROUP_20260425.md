# Current Worktree Closeout Tooling Group - Development And Verification

Date: 2026-04-25

## 1. Goal

Add a dedicated closeout helper split group for tooling so the helper itself can be
reviewed and staged without mixing runtime closeout docs or router/Odoo hardening work.

## 2. Group Definition

Added group: `closeout-tooling` in
[`scripts/print_current_worktree_closeout_commands.sh`](scripts/print_current_worktree_closeout_commands.sh)

Scope:

- `scripts/print_current_worktree_closeout_commands.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_current_worktree_closeout_commands.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_PR_SPLIT_COMMANDS_20260425.md`
- `docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_ROUTER_STAGING_SCOPE_GUARD_20260425.md`
- `docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_TOOLING_GROUP_20260425.md`
- `.github/workflows/ci.yml`

Contract intent:

- Keep the helper read-only.
- Preserve `.claude/` and `local-dev-env/` as local-only exclusions.
- Keep route-family staging narrow and non-broad.

## 3. Verification

Commands captured in this closeout run:

```bash
.venv/bin/python -m pytest -q \
src/yuantus/meta_engine/tests/test_ci_contracts_current_worktree_closeout_commands.py

.venv/bin/python -m pytest -q \
src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py

.venv/bin/python -m pytest -q \
src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py

.venv/bin/python -m pytest -q \
src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py

git diff --check

bash -n scripts/print_current_worktree_closeout_commands.sh

bash scripts/print_current_worktree_closeout_commands.sh --commands
```

Observed results:

- test_ci_contracts_current_worktree_closeout_commands.py: passed (1)
- test_ci_shell_scripts_syntax.py: passed (18)
- test_ci_contracts_ci_yml_test_list_order.py + test_ci_contracts_job_wiring.py: passed (2 + 2)
- test_delivery_scripts_index_entries_contracts.py: passed (2)
- git diff --check: clean
- script syntax check: ok
- `print_current_worktree_closeout_commands.sh` command output includes:
  - four groups (including `closeout-tooling`)
  - local-only exclusion list
  - all group command templates

## 4. Non-Goals

- No commit or push.
- No automatic `git add` or merge execution.
- No runtime behavior change for Odoo18 verifier, router runtime, or business logic.
