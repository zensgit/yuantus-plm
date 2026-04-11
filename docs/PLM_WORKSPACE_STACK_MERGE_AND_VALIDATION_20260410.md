# PLM Workspace Stack Merge And Validation

Date: `2026-04-10`
Primary branch closeout: `#173 -> #176 -> #175`
Post-merge hotfix: `#177`
Main tip after completion: `bcf02dda17706a55f116b3048450cb045608de0c`

## Summary

This closeout merged the native PLM workspace browser-regression stack into
`main` using merge commits, then ran a merged-main verification pass in a clean
worktree.

The intended three-slice stack was:

1. document handoff roundtrips
2. release readiness drilldown coverage
3. ECO source recovery roundtrip

During execution, the original readiness PR [#174](https://github.com/zensgit/yuantus-plm/pull/174)
was automatically closed when its stacked base branch was merged and deleted.
That slice was re-opened correctly as replacement PR
[#176](https://github.com/zensgit/yuantus-plm/pull/176) against `main`.

Merged-main validation then found one real regression in the change demo:
`Load Approval Rail` could return an empty generic approval summary instead of
triggering the ECO-native fallback. That was fixed immediately in
[#177](https://github.com/zensgit/yuantus-plm/pull/177).

## PR Stack

### 1. Document handoff bundle

- PR: [#173](https://github.com/zensgit/yuantus-plm/pull/173)
- Title: `feat(plm-workspace): harden document handoff roundtrips`
- Base / Head: `main` <- `feature/claude-c43-cutted-parts-throughput`
- State: `MERGED`
- Merged at: `2026-04-10T14:50:01Z`
- Merge SHA: `09c999b692c438490ead17197da1e571e6344e65`

Outcome:

- landed document source roundtrips for product / detail / change / documents
- locked document-tab stability with browser regressions
- landed BOM demo resume coverage and ECO approval rail fallback groundwork

### 2. Release readiness drilldown slice

- Original PR: [#174](https://github.com/zensgit/yuantus-plm/pull/174)
- State: `CLOSED`
- Closed at: `2026-04-10T14:50:20Z`
- Reason: original stacked base branch was merged and deleted before retarget
- Replacement PR: [#176](https://github.com/zensgit/yuantus-plm/pull/176)
- Title: `feat(plm-workspace): add release readiness drilldown coverage`
- Base / Head: `main` <- `codex/plm-workspace-readiness-drilldown-20260410`
- State: `MERGED`
- Merged at: `2026-04-10T14:55:56Z`
- Merge SHA: `7f644ea6f10b926a3459bd4dd010080f45abd874`

Outcome:

- added non-empty release readiness demo fixture coverage
- locked readiness rail / detail lens behavior in browser regression
- boundary-limited unsupported readiness resource handoffs in native workspace

### 3. ECO source recovery slice

- PR: [#175](https://github.com/zensgit/yuantus-plm/pull/175)
- Title: `feat(plm-workspace): add eco source recovery roundtrip`
- Base / Head: `main` <- `codex/plm-workspace-eco-source-recovery-20260410`
- State: `MERGED`
- Merged at: `2026-04-10T14:56:46Z`
- Merge SHA: `8adb4ae110ee140e8bca385719fd9bbfdafbed6d`

Outcome:

- preserved `handoffSource` through ECO detail flow
- added `Return to Source Change` from ECO detail
- restored source `Part` change surfaces without leaking ECO-only recovery copy

### 4. Merged-main hotfix

- PR: [#177](https://github.com/zensgit/yuantus-plm/pull/177)
- Title: `fix(plm-workspace): fallback to eco governance on empty approval rail`
- Base / Head: `main` <- `codex/plm-workspace-eco-approval-fallback-20260410`
- State: `MERGED`
- Merged at: `2026-04-10T15:06:39Z`
- Merge SHA: `bcf02dda17706a55f116b3048450cb045608de0c`

Outcome:

- fixed merged-main regression discovered during post-merge validation
- when `/approvals/*` returns an empty rail for an ECO-driven `Part` flow, the
  native workspace now switches to ECO-native governance fallback instead of
  showing an empty generic approval summary
- no public API or contract changes

## Design Outcome

### Document handoff

- Native workspace now has stable browser-locked roundtrips for:
  - source product
  - source detail
  - source change
  - source documents
- Related AML documents keep document-only boundaries while active.
- Returning to the source `Part` restores the correct surface without stale
  document state leakage.

### Release readiness

- The `Config Parent` demo can now hydrate a non-empty readiness rail with BOM,
  MBOM, workcenter, routing, and baseline support data.
- `Resource Detail Lens` is browser-locked.
- Unsupported readiness resources remain inspectable but are explicitly
  boundary-limited instead of pretending they are native first-class workspace
  objects.

### ECO source recovery

- `Part -> ECO -> Return to Source Change` is now a stable browser-locked flow.
- Returning from ECO restores:
  - `Change Snapshot`
  - `Release Snapshot`
  - `Recent ECO Activity`
- ECO-specific source-recovery copy no longer leaks into the restored source
  `Part` view.

### Approval rail behavior after merge

- The merged-main validation pass found a real regression:
  `Load Approval Rail` returned a `200` with an empty generic approval summary,
  so the earlier `404`-only fallback logic did not trigger.
- `#177` fixes that by switching to ECO-native governance fallback when:
  - the object supports governance
  - there is ECO context for the current `Part`
  - generic approval summary / request / queue-health totals are all zero

## Verification

### GitHub checks

#### `#173`

- `detect_changes (CI)`: `SUCCESS`
- `detect_changes (regression)`: `SUCCESS`
- `contracts`: `SUCCESS`
- `plugin-tests`: `SUCCESS`
- `regression`: `SUCCESS`
- `playwright-esign`: `SKIPPED`
- `cad_ml_quick`: `SKIPPED`
- `cadgf_preview`: `SKIPPED`

#### `#176`

- `detect_changes (CI)`: `SUCCESS`
- `detect_changes (regression)`: `SUCCESS`
- `contracts`: `SUCCESS`
- `plugin-tests`: `SUCCESS`
- `regression`: `SUCCESS`
- `playwright-esign`: `SKIPPED`
- `cad_ml_quick`: `SKIPPED`
- `cadgf_preview`: `SKIPPED`

#### `#175`

- `detect_changes (CI)`: `SUCCESS`
- `detect_changes (regression)`: `SUCCESS`
- `contracts`: `SKIPPED`
- `plugin-tests`: `SUCCESS`
- `regression`: `SUCCESS`
- `playwright-esign`: `SUCCESS`
- `cad_ml_quick`: `SKIPPED`
- `cadgf_preview`: `SKIPPED`

#### `#177`

- `detect_changes (CI)`: `SUCCESS`
- `detect_changes (regression)`: `SUCCESS`
- `contracts`: `SKIPPED`
- `plugin-tests`: `SUCCESS`
- `regression`: `SUCCESS`
- `playwright-esign`: `SUCCESS`
- `cad_ml_quick`: `SKIPPED`
- `cadgf_preview`: `SKIPPED`

### Local merged-main validation

Validation was rerun against a clean detached worktree at merged `origin/main`.
Because `node_modules` and `.venv` are ignored local dependencies, the clean
worktree reused the existing installed environment via symlinks.

Executed results:

- `./.venv/bin/python -m pytest src/yuantus/api/tests/test_plm_workspace_router.py src/yuantus/api/tests/test_workbench_router.py -q`
  - Result: `7 passed in 7.31s`
- `npx playwright test playwright/tests/plm_workspace_document_handoff.spec.js`
  - Result: `6 passed (12.0s)`
- `npx playwright test playwright/tests/plm_workspace_demo_resume.spec.js`
  - First run on merged main exposed the empty generic approval-rail regression
  - After `#177` hotfix: `3 passed (9.0s)`
- `npx playwright test playwright/tests/plm_workspace_documents_ui.spec.js playwright/tests/plm_workspace_demo_resume.spec.js playwright/tests/plm_workspace_document_handoff.spec.js`
  - Final result after `#177`: `11 passed (9.4s)`

### Mainline closeout

- `main` now includes the three intended slices plus the merged-main hotfix.
- No stacked PR remains open for the readiness or ECO source-recovery branches.
- The old readiness PR [#174](https://github.com/zensgit/yuantus-plm/pull/174)
  is intentionally left closed and superseded by `#176`.
- The latest fetched `origin/main` is:
  - `bcf02dda17706a55f116b3048450cb045608de0c`

## Notes

- This round intentionally stopped stacking new feature PRs and cleared the
  green stack first.
- Merge strategy was `merge commit` throughout to preserve stacked ancestry and
  keep retargeted diffs comprehensible.
- All merge / retarget work was done outside the dirty primary worktree.
- The next implementation branch should start from fresh `main` at:
  - `bcf02dda17706a55f116b3048450cb045608de0c`
