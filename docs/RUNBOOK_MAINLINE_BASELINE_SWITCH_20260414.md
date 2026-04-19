# Mainline Baseline Switch Runbook

Use this runbook when the current feature branch is dirty and no longer matches
the real merged baseline on `origin/main`.

This repo is in exactly that situation on `2026-04-14`:

- current branch: `feature/claude-c43-cutted-parts-throughput`
- true merged P0/P1 baseline: `origin/main`
- current branch is behind `origin/main` by `135` commits

See:

- [Baseline Correction Audit](./DEV_AND_VERIFICATION_BASELINE_CORRECTION_AUDIT_20260414.md)
- [Branch Merge/Rebase Risk Audit](./DEV_AND_VERIFICATION_BRANCH_MERGE_RISK_AUDIT_20260414.md)

## Goal

Preserve the current dirty worktree safely, then move ongoing development to a
clean `origin/main` worktree.

## Why this is recommended

The current branch has only a small number of unique committed changes, but the
working tree is very dirty. The actual risk is not the 6 unique commits; it is
mixing those commits with a large set of uncommitted files while trying to
reason about P0/P1 baseline state.

## Recommended flow

### 1. Inspect the current tree

```bash
git status --short
git rev-list --left-right --count feature/claude-c43-cutted-parts-throughput...origin/main
```

### 2. Preserve the current tree before any switch

Create a backup branch at the current `HEAD`:

```bash
git branch backup/feature-claude-c43-cutted-parts-throughput-<stamp> HEAD
```

Archive both unstaged and staged patches:

```bash
git diff --binary > /tmp/yuantus-<stamp>.patch
git diff --cached --binary > /tmp/yuantus-<stamp>-staged.patch
```

Stash the full dirty tree, including untracked files:

```bash
git stash push -u -m 'baseline-switch <stamp>'
```

### 3. Create a clean `origin/main` worktree

```bash
mkdir -p ../Yuantus-worktrees
git worktree add -b baseline/mainline-<stamp> \
  ../Yuantus-worktrees/mainline-<stamp> origin/main
```

Using a dedicated local branch is preferred over a detached worktree when the
new worktree is meant to become an ongoing development baseline.

### 4. Before editing, cut a real topic branch in the new worktree

```bash
git -C ../Yuantus-worktrees/mainline-<stamp> switch -c feature/<topic>-<YYYYMMDD>
```

This keeps:

- `baseline/mainline-<stamp>` as the clean reference branch
- `feature/<topic>-<YYYYMMDD>` as the writable development branch

If you are operating inside one of the constrained `Claude C*` tracks, use the
corresponding branch pattern from `contracts/claude_allowed_paths.json`, for
example `feature/claude-c12-<slug>`.

### 5. Re-apply only what still matters

Current-branch unique commits:

1. `f9076f4` `feat(plm-workspace): harden document handoff flow`
2. `09b30e2` `test(plm-workspace): tighten document flow html assertions`
3. `e42c79e` `test(plm-workspace): lock source-change document roundtrip`
4. `d24b5a4` `docs(pact): add aml metadata verification note`
5. `6738eac` `docs(aml): add metadata federation and index`
6. `a50f400` `docs(aml): add session handoff`

Re-apply them in a clean worktree only if they are still wanted:

```bash
git cherry-pick f9076f4 09b30e2 e42c79e d24b5a4 6738eac a50f400
```

### 6. Keep Claude Code isolated if you use it later

This repo already has a dedicated runbook:

- [Claude Code Parallel Worktree Runbook](./RUNBOOK_CLAUDE_CODE_PARALLEL_WORKTREE.md)

If `claude auth status` shows `loggedIn: true`, prefer using Claude in the
clean worktree, not the dirty primary tree.

## Command generator

Use the helper script to print a ready-to-run sequence:

```bash
bash scripts/print_mainline_baseline_switch_commands.sh
```

If you already know the next topic branch name, print a fully resolved command
set with:

```bash
bash scripts/print_mainline_baseline_switch_commands.sh \
  --topic-branch feature/<topic>-<YYYYMMDD>
```

## Important cautions

- Do not treat the current dirty branch as if it were the already-merged P0/P1 baseline.
- Do not rebase a dirty worktree directly onto `origin/main`.
- Do not replay all local changes blindly; replay by topic.
- Keep `plm_workspace.html` and related Playwright/tests isolated, because that
  is the main committed overlap hotspot between the current branch and
  `origin/main`.

## Claude Code CLI

`Claude Code CLI` can be invoked from this machine, but as of this run it is
not usable for development because the CLI is not logged in:

```bash
claude -p --output-format text 'say ok'
```

Result:

```text
Not logged in · Please run /login
```

So the safe path today is:

- preserve the current tree
- create a clean `origin/main` worktree
- continue with Codex or a logged-in Claude session later
