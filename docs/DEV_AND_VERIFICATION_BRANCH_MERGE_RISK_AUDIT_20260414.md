# Branch Merge/Rebase Risk Audit

Date: 2026-04-14

## Scope

Assess the safest path from the current working branch
`feature/claude-c43-cutted-parts-throughput`
to the actual merged P0/P1 baseline on `origin/main`.

## Summary

- `origin/main` already contains the P0 convergence branches and later P1 baseline work.
- The current feature branch does **not** contain those merges.
- The current branch unique commit history is narrow and mostly PLM workspace/UI-doc/test work.
- The practical merge risk is dominated by the **dirty working tree**, not by the 6 unique commits.

## Git Evidence

Current refs:

- `feature/claude-c43-cutted-parts-throughput`: `a50f400`
- `platform/plm-core-convergence`: `1de3c4a`
- `platform/plm-p02-eco-permission-adapter`: `f71ae2b`
- `platform/plm-p03-eco-routing-change`: `43b1888`
- `origin/main`: `1c78a18`

Common merge-base:

```bash
git merge-base feature/claude-c43-cutted-parts-throughput origin/main
```

Result:

- `7f4a481f71a3135c5047d5e33a504cb4d56c60b6`

Divergence counts:

```bash
git rev-list --left-right --count feature/claude-c43-cutted-parts-throughput...origin/main
git rev-list --left-right --count feature/claude-c43-cutted-parts-throughput...platform/plm-core-convergence
git rev-list --left-right --count feature/claude-c43-cutted-parts-throughput...platform/plm-p02-eco-permission-adapter
git rev-list --left-right --count feature/claude-c43-cutted-parts-throughput...platform/plm-p03-eco-routing-change
```

Results:

- current vs `origin/main`: `6 135`
- current vs `platform/plm-core-convergence`: `6 128`
- current vs `platform/plm-p02-eco-permission-adapter`: `6 129`
- current vs `platform/plm-p03-eco-routing-change`: `6 129`

## Current Branch Unique Commits

```bash
git log --oneline origin/main..feature/claude-c43-cutted-parts-throughput
```

Unique commits:

1. `a50f400` docs(aml): add session handoff
2. `6738eac` docs(aml): add metadata federation and index
3. `d24b5a4` docs(pact): add aml metadata verification note
4. `e42c79e` test(plm-workspace): lock source-change document roundtrip
5. `09b30e2` test(plm-workspace): tighten document flow html assertions
6. `f9076f4` feat(plm-workspace): harden document handoff flow

Interpretation:

- These commits do not overlap the bulk of P0 convergence implementation.
- They mainly touch `plm_workspace` HTML/tests/docs.

## Committed Branch Conflict Hotspots

Overlap between current branch unique commits and `origin/main` since merge-base is small:

- `playwright/tests/README_plm_workspace.md`
- `playwright/tests/plm_workspace_document_handoff.spec.js`
- `src/yuantus/api/tests/test_plm_workspace_router.py`
- `src/yuantus/web/plm_workspace.html`

The largest committed conflict hotspot is:

- `src/yuantus/web/plm_workspace.html`

Diff summary:

```bash
git diff --stat origin/main..feature/claude-c43-cutted-parts-throughput -- \
  playwright/tests/README_plm_workspace.md \
  playwright/tests/plm_workspace_document_handoff.spec.js \
  src/yuantus/api/tests/test_plm_workspace_router.py \
  src/yuantus/web/plm_workspace.html
```

Result:

- `plm_workspace.html`: large rewrite / deletion-heavy conflict surface

## Actual High-Risk Factor

The current worktree is dirty and includes many uncommitted modifications and untracked files
across:

- ECO / approvals / routing / subcontracting
- CAD pipeline / file router / version services
- docs / delivery notes / scripts

That is the real merge risk.

Without isolating or shelving the dirty worktree first, any rebase/merge attempt will be noisy
and hard to reason about.

## Recommended Strategy

### Best option

1. Preserve the current dirty worktree into a safety branch or stash.
2. Start a clean worktree from `origin/main`.
3. Re-apply only the 6 current-branch unique commits if they are still wanted.
4. Re-apply selected uncommitted changes intentionally, by topic.

### If you must stay on the current branch

1. Commit or stash all current uncommitted changes first.
2. Merge `origin/main` into the current branch rather than rebasing immediately.
3. Resolve the small committed overlap first:
   - `src/yuantus/web/plm_workspace.html`
   - `playwright/tests/plm_workspace_document_handoff.spec.js`
   - `src/yuantus/api/tests/test_plm_workspace_router.py`
4. Only after that, replay the local dirty worktree topics one by one.

## Recommendation

Do **not** continue long-term development on the current dirty branch as if it were the P0/P1 baseline.

Use a clean `origin/main` worktree as the true baseline.

## Claude Code CLI

`Claude Code CLI` can be invoked as a command, but it is not usable in the current environment:

```bash
claude -p --output-format text 'say ok'
```

Result:

- `Not logged in · Please run /login`

So it cannot currently execute development tasks unless the environment is logged in first.
