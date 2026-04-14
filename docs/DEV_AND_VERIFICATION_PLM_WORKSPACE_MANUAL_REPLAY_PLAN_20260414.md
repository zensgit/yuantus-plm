# PLM Workspace Manual Replay Plan

Date: 2026-04-14

## Goal

Assess whether any `plm_workspace` changes from
`feature/claude-c43-cutted-parts-throughput`
still need replay on top of the clean `origin/main` baseline worktree.

## Why automatic replay was rejected

Automatic `cherry-pick` of the recommended workspace commit failed immediately
on the predicted hotspots:

- `src/yuantus/web/plm_workspace.html`
- `src/yuantus/api/tests/test_plm_workspace_router.py`
- `playwright/tests/plm_workspace_document_handoff.spec.js`

The clean worktree was left untouched by aborting that cherry-pick.

## Updated conclusion

After inspecting `origin/main` and re-running the current mainline workspace
router contract test, the old branch's visible `plm_workspace` behavior is
already substantially present on `origin/main`.

Evidence:

- `origin/main` already contains:
  - `playwright/tests/plm_workspace_document_handoff.spec.js`
  - `src/yuantus/api/tests/test_plm_workspace_router.py`
  - document-handoff strings such as:
    - `Document Boundary`
    - `Document Focus`
    - `Governance Boundary`
    - `Return to Source Documents`
    - `Not published for this object`
    - `Recent ECO Activity`
- Verification:

```bash
PYTHONPATH=src python3 -m pytest -q src/yuantus/api/tests/test_plm_workspace_router.py
```

Result:

- `3 passed, 1 warning`

So these old commits should now be treated as **reference material**, not as a
mandatory replay queue.

## Source commits

Current branch unique commits:

1. `f9076f4` `feat(plm-workspace): harden document handoff flow`
2. `09b30e2` `test(plm-workspace): tighten document flow html assertions`
3. `e42c79e` `test(plm-workspace): lock source-change document roundtrip`
4. `d24b5a4` `docs(pact): add aml metadata verification note`
5. `6738eac` `docs(aml): add metadata federation and index`
6. `a50f400` `docs(aml): add session handoff`

## Replay recommendation

### Code commits

Do not replay these automatically:

- `f9076f4`
- `09b30e2`
- `e42c79e`

Use them only as diff references if a later gap is discovered in:

- `src/yuantus/web/plm_workspace.html`
- `src/yuantus/api/tests/test_plm_workspace_router.py`
- `playwright/tests/plm_workspace_document_handoff.spec.js`

### Docs commits

Still optional and low risk:

- `d24b5a4`
- `6738eac`
- `a50f400`

## Implementation order if a future gap is found

1. prove the gap against current `origin/main`
2. port only the missing behavior into `plm_workspace.html`
3. update the FastAPI HTML contract test
4. update the Playwright handoff spec
5. rerun only the workspace-focused tests

## Suggested verification

```bash
python3 -m pytest -q src/yuantus/api/tests/test_plm_workspace_router.py
python3 -m pytest -q playwright/tests/plm_workspace_document_handoff.spec.js
```

If the Playwright command requires repo-local wrappers, use the repo’s existing
workspace scripts instead of inventing new ones.

## Claude Code CLI

`claude auth status` is now logged in, so Claude can be used in this clean
worktree.

Recommended pattern:

```bash
claude --worktree mainline-20260414-150835 --add-dir /Users/chouhua/Downloads/Github/Yuantus \
  'In the clean origin/main worktree, manually replay only the plm_workspace document handoff feature into the current workspace implementation. Keep the diff small and reviewable.'
```

Do not use Claude against the old dirty feature branch.
