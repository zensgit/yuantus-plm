# Mainline Baseline Switch Preview

Date: 2026-04-14

## Goal

Expand the baseline-switch flow into concrete commands for the current machine,
current repo path, and current branch, without executing any branch surgery.

## Current context

- repo: `/Users/chouhua/Downloads/Github/Yuantus`
- current branch: `feature/claude-c43-cutted-parts-throughput`
- target baseline: `origin/main`
- current branch divergence from `origin/main`: `ahead 6 / behind 135`

## Previewed command sequence

Generated via:

```bash
bash scripts/print_mainline_baseline_switch_commands.sh
```

Preview:

```bash
git -C /Users/chouhua/Downloads/Github/Yuantus status --short
git -C /Users/chouhua/Downloads/Github/Yuantus rev-list --left-right --count feature/claude-c43-cutted-parts-throughput...origin/main

git -C /Users/chouhua/Downloads/Github/Yuantus branch backup/feature-claude-c43-cutted-parts-throughput-<stamp> HEAD
git -C /Users/chouhua/Downloads/Github/Yuantus diff --binary > /tmp/Yuantus-<stamp>.patch
git -C /Users/chouhua/Downloads/Github/Yuantus diff --cached --binary > /tmp/Yuantus-<stamp>-staged.patch
git -C /Users/chouhua/Downloads/Github/Yuantus stash push -u -m 'baseline-switch <stamp>'

mkdir -p /Users/chouhua/Downloads/Github/Yuantus-worktrees
git -C /Users/chouhua/Downloads/Github/Yuantus worktree add /Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-<stamp> origin/main

git -C /Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-<stamp> cherry-pick \
  f9076f4 09b30e2 e42c79e d24b5a4 6738eac a50f400
```

## Current branch unique commits

```text
f9076f4 feat(plm-workspace): harden document handoff flow
09b30e2 test(plm-workspace): tighten document flow html assertions
e42c79e test(plm-workspace): lock source-change document roundtrip
d24b5a4 docs(pact): add aml metadata verification note
6738eac docs(aml): add metadata federation and index
a50f400 docs(aml): add session handoff
```

## Claude Code CLI status

Unlike the earlier baseline audit, the current environment is now authenticated:

```bash
claude auth status
```

Observed:

```json
{
  "loggedIn": true,
  "authMethod": "claude.ai",
  "apiProvider": "firstParty"
}
```

So Claude Code can now be used, but it should still be used in a clean
worktree rather than the dirty primary tree.

Recommended invocation pattern:

```bash
claude --worktree mainline-<stamp> --add-dir /Users/chouhua/Downloads/Github/Yuantus \
  'Work only in the clean origin/main baseline worktree. Re-apply the minimal current-branch deltas, keep the scope narrow, and inspect git status first.'
```

## Verification

### Script output smoke

```bash
bash scripts/print_mainline_baseline_switch_commands.sh | sed -n '1,120p'
```

Result:

- passed

### Claude auth probe

```bash
claude auth status
```

Result:

- logged in

## Outcome

This preview is ready for operator execution, but no branch-modifying commands
were executed as part of this document.
