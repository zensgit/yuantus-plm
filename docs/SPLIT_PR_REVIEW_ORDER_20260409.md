# Split PR Review Order

Date: `2026-04-09`
Repository: `zensgit/yuantus-plm`

This note gives the shortest reviewer routing order across the main native
workspace PR and the three extracted residual split PRs.

## Recommended Order

1. `#155`
   Review the main native-workspace / browser-harness branch on its own scope first.
   It is already isolated from the residual splits and should not be widened.
2. `#156`
   Review the code-facing router residual split next.
   This is the only extracted split that changes runtime behavior and tests.
3. `#157` and `#158`
   Review these two doc-only splits in parallel after `#156`, or independently if
   the reviewers only care about doc hygiene.

## Routing Rule

- `#155` remains the primary product review thread
- `#156` is the first follow-up code review
- `#157` and `#158` are doc-only follow-ups and do not block each other
- do **not** re-bundle the split PRs back into `#155`

## References

- `docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md`
- `docs/SPLIT_BRANCHES_SUMMARY_20260409.md`
- `docs/SPLIT_BRANCH_PR_DRAFTS_20260409.md`
