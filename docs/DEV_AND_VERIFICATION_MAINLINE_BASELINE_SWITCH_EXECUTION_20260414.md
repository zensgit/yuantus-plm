# Mainline Baseline Switch Execution

Date: 2026-04-14

## Goal

Record the baseline switch that was actually executed:

1. preserve the dirty `feature/claude-c43-cutted-parts-throughput` worktree
2. create a clean `origin/main` worktree for ongoing development
3. verify whether current-branch `plm_workspace` commits still need replay
4. verify current `Claude Code CLI` availability in the clean worktree

## Executed Preservation Steps

The original dirty worktree stayed at:

- repo: `/Users/chouhua/Downloads/Github/Yuantus`
- branch: `feature/claude-c43-cutted-parts-throughput`

Preservation artifacts created before the switch:

- backup branch:
  - `backup/feature-claude-c43-cutted-parts-throughput-20260414-150835`
- patch files:
  - `/tmp/Yuantus-20260414-150835.patch`
  - `/tmp/Yuantus-20260414-150835-staged.patch`
  - `/tmp/Yuantus-20260414-150835-status.txt`
- stash:
  - `stash@{0}: On feature/claude-c43-cutted-parts-throughput: baseline-switch 20260414-150835`

## Clean Worktree Created

New clean baseline worktree:

- path: `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260414-150835`
- branch: `baseline/mainline-20260414-150835`
- source ref: `origin/main`

Verification at creation time:

```bash
git rev-list --left-right --count HEAD...origin/main
```

Observed:

- `0 0`

So the new worktree started as an exact clean mainline baseline.

## Replay Attempt And Outcome

The previously recommended `plm_workspace` replay commits were tested in the
clean worktree:

- `f9076f4`
- `09b30e2`
- `e42c79e`

The first `cherry-pick` conflicted immediately in:

- `src/yuantus/web/plm_workspace.html`
- `playwright/tests/plm_workspace_document_handoff.spec.js`
- `src/yuantus/api/tests/test_plm_workspace_router.py`

The cherry-pick was then aborted:

```bash
git cherry-pick --abort
```

This left the clean worktree on pure `origin/main`.

## Updated Replay Decision

After re-checking the clean mainline implementation, these 3 commits are no
longer treated as a replay queue. They are now reference-only diffs.

Evidence:

- `origin/main` already contains:
  - `playwright/tests/plm_workspace_document_handoff.spec.js`
  - `src/yuantus/api/tests/test_plm_workspace_router.py`
- current mainline router contract test passes:

```bash
PYTHONPATH=src python3 -m pytest -q src/yuantus/api/tests/test_plm_workspace_router.py
```

Observed:

- `3 passed, 1 warning`

See also:

- [PLM Workspace Manual Replay Plan](./DEV_AND_VERIFICATION_PLM_WORKSPACE_MANUAL_REPLAY_PLAN_20260414.md)

## Verification Run In The Clean Worktree

Smoke regression:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/api/tests/test_plm_workspace_router.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py
```

Observed:

- `27 passed, 1 warning`

The warning is the existing local `urllib3/LibreSSL` environment warning. It is
not a new regression from the baseline switch.

## Claude Code CLI Status

Earlier baseline docs captured a pre-login state where `claude -p` was not yet
usable. That is now superseded by this execution record.

Current verification in the clean worktree:

```bash
claude auth status
claude -p "Reply with exactly: OK"
```

Observed:

- `claude auth status` reports `loggedIn: true`
- the short non-interactive probe returned `OK`

Practical note:

- simple probes work
- longer `claude -p` prompts in this terminal may still be less predictable
- the recommended usage pattern remains: run Claude in the clean worktree, not
  the old dirty feature branch

## Outcome

The repo now has a real clean mainline development baseline:

- keep ongoing work in
  `/Users/chouhua/Downloads/Github/Yuantus-worktrees/mainline-20260414-150835`
- do not continue feature work on the old dirty branch as if it were the merged
  P0/P1 baseline
- treat the old `plm_workspace` commits as reference-only unless a concrete gap
  is proven against current `origin/main`
