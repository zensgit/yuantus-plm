# Development And Verification

Date: 2026-04-14

## Goal

Provide a safe, repo-local procedure for:

1. preserving the current dirty feature worktree
2. switching to a clean `origin/main` baseline worktree
3. keeping optional Claude Code usage isolated behind an authenticated
   worktree flow

## Deliverables

- [RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md](./RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md)
- `scripts/print_mainline_baseline_switch_commands.sh`

## Design choices

- The script prints commands instead of executing them.
- The flow preserves three recovery artifacts:
  - backup branch
  - unstaged patch
  - staged patch
- The flow still prints a `git stash -u` step because the practical next action
  is to get to a clean worktree quickly.
- Claude Code is kept optional and gated behind `claude auth status`.

## Verification

### Script syntax

```bash
bash -n scripts/print_mainline_baseline_switch_commands.sh
```

Result:

- passed

### Script output smoke

```bash
bash scripts/print_mainline_baseline_switch_commands.sh | sed -n '1,120p'
```

Result:

- printed the expected 6-step sequence:
  - inspect
  - preserve
  - create worktree
  - cherry-pick unique commits
  - optional Claude worktree command
  - rollback references

### Baseline evidence reused

The runbook content is grounded in these verified branch facts:

```bash
git merge-base feature/claude-c43-cutted-parts-throughput origin/main
git rev-list --left-right --count feature/claude-c43-cutted-parts-throughput...origin/main
git log --oneline origin/main..feature/claude-c43-cutted-parts-throughput
```

Observed:

- merge-base: `7f4a481f71a3135c5047d5e33a504cb4d56c60b6`
- divergence: `6 135`
- current branch unique commits: 6

### Claude Code CLI probe

```bash
claude -p --output-format text 'say ok'
```

Observed:

```text
Not logged in · Please run /login
```

So the runbook correctly treats Claude Code as unavailable for real execution in
the current environment.

## Outcome

The repo now has a documented and scriptable path to:

- stop treating the current dirty branch as the merged baseline
- preserve local work safely
- switch ongoing development to a clean `origin/main` worktree
