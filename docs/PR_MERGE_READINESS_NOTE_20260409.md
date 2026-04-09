# PR Merge Readiness Note

Date: `2026-04-09`
Repository: `zensgit/yuantus-plm`

This note gives the shortest merge-readiness view across the main native
workspace PR and the three extracted residual split PRs.

## Merge Rule

- `#155` stays on native workspace / browser-harness scope
- `#156`, `#157`, and `#158` stay as separate follow-up PRs
- do **not** re-bundle the split PRs back into `#155`

## Merge Order

1. `#155`
   Merge when the native workspace reviewer sign-off is complete and the
   workspace verification path is green.
2. `#156`
   Merge after `#155`, or immediately after its own router/runtime review if the
   branches remain conflict-free.
3. `#157`
   Merge independently after doc-governance review.
4. `#158`
   Merge independently after product-doc review.

## Merge Checks

### `#155`

- reviewer uses `docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md`
- native workspace bundle scope remains isolated
- browser harness / wrapper verification is green
- reviewer is comfortable ignoring split follow-ups from this PR

### `#156`

- router/runtime reviewer sign-off is complete
- local router test command is green
- PR stays limited to the 5 extracted router files

### `#157`

- doc-governance reviewer sign-off is complete
- PR stays limited to the 3 extracted governance/operator docs

### `#158`

- product-doc reviewer sign-off is complete
- PR stays limited to the 2 extracted product strategy docs

## Non-Blocking Rule

- `#157` does not block `#158`
- `#158` does not block `#157`
- neither doc-only follow-up blocks `#155`
- doc-only follow-ups should not be used to reopen review scope on `#155`

## Reviewer Entrypoints

- `docs/PR_CLOSE_DECISION_NOTE_20260409.md`
- `docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md`
- `docs/PR_TRIAGE_SUMMARY_20260409.md`
- `docs/PR_REVIEWER_ASSIGNMENT_PLAN_20260409.md`
- `docs/SPLIT_PR_REVIEW_ORDER_20260409.md`

## One-Line Operator Rule

Merge `#155` on its own workspace scope first, then merge `#156`, and let `#157`
and `#158` flow independently as doc-only follow-ups.
