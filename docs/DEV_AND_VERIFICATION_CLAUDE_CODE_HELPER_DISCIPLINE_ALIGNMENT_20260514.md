# Dev & Verification - Claude Code Helper Discipline Alignment

Date: 2026-05-14

## 1. Summary

Aligned the existing Claude Code helper scripts with the assist discipline
introduced in `docs/DEV_AND_VERIFICATION_CLAUDE_CODE_ASSIST_DISCIPLINE_20260514.md`.

This is a helper/tooling closeout. It does not start Phase 5, does not create
P3.4 evidence, and does not change runtime behavior.

## 2. Files Changed

- `scripts/print_claude_code_parallel_commands.sh`
- `scripts/run_claude_code_parallel_reviewer.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_parallel_helper.py`
- `docs/DEV_AND_VERIFICATION_CLAUDE_CODE_HELPER_DISCIPLINE_ALIGNMENT_20260514.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The previous helper templates still printed older `claude -p --add-dir ...`
read-only commands. The runbook now pins a stricter read-only shape:

```bash
printf '%s\n' '<read-only prompt>' | claude -p --no-session-persistence --tools ""
```

This change updates the helper scripts so the printed and executable reviewer
paths match that discipline.

## 4. Behavior

- `print_claude_code_parallel_commands.sh --mode read-only` now emits a
  subshell that `cd`s into the target repo and pipes the prompt into
  `claude -p --no-session-persistence --tools ""`.
- `print_claude_code_parallel_commands.sh --mode reviewer` uses the same
  read-only CLI shape.
- `print_claude_code_parallel_commands.sh --mode worktree` remains a write-mode
  template, but now explicitly says it requires user authorization and forbids
  permission-skipping modes plus `.claude/` / `local-dev-env/` commits.
- `run_claude_code_parallel_reviewer.sh` now executes the stricter read-only
  shape directly from inside the target repo.

## 5. Claude Code Assist

Claude Code was used read-only to recommend the smallest safe continuation and
confirm that Phase 5/P3.4 should remain blocked. It did not edit files.

## 6. Non-Goals

- No runtime code changes.
- No Phase 5 implementation.
- No P3.4 evidence synthesis or cutover enablement.
- No new Claude Code helper script.
- No use of Claude Code write mode.

## 7. Verification Commands

```bash
bash scripts/print_claude_code_parallel_commands.sh --mode read-only
bash scripts/print_claude_code_parallel_commands.sh --mode reviewer
bash scripts/print_claude_code_parallel_commands.sh --mode worktree --worktree-name claude-test-scope
bash scripts/run_claude_code_parallel_reviewer.sh --help

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_parallel_helper.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_assist_discipline.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

git diff --check
```

## 8. Verification Results

- Shell syntax (`bash -n` on both helper scripts): passed.
- Template smoke:
  - `print_claude_code_parallel_commands.sh --mode read-only`: passed.
  - `print_claude_code_parallel_commands.sh --mode reviewer`: passed.
  - `print_claude_code_parallel_commands.sh --mode worktree --worktree-name claude-test-scope`: passed.
  - `run_claude_code_parallel_reviewer.sh --help`: passed.
- Focused contract suite:
  - Claude Code parallel helper contract
  - Claude Code assist discipline contract
  - shell scripts syntax contract
  - doc-index trio
  - CI list-order contract
  - Result: `28 passed`.
- `git diff --check`: clean.

## 9. Review Checklist

- Confirm no runtime code changed.
- Confirm read-only helper output uses `--no-session-persistence --tools ""`.
- Confirm reviewer script no longer uses `claude -p --add-dir`.
- Confirm worktree mode still requires explicit authorization.
- Confirm `.claude/` and `local-dev-env/` remain untracked only.

This file is indexed as
`docs/DEV_AND_VERIFICATION_CLAUDE_CODE_HELPER_DISCIPLINE_ALIGNMENT_20260514.md`.
