# PR Close Decision Note

Date: `2026-04-09`
Repository: `zensgit/yuantus-plm`
Primary PR: `zensgit/yuantus-plm#155`

This note gives the shortest close decision for the main native workspace PR.

## Merge Now If

- the reviewer has completed `docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md`
- native workspace scope remains isolated from the split follow-up PRs
- local workspace verification is green for the documented commands
- the reviewer is comfortable ignoring `#156`, `#157`, and `#158` as separate
  follow-up PRs

## Hold If

- review scope starts expanding from `#155` into router/doc follow-up work
- someone attempts to re-bundle `#156`, `#157`, or `#158` back into `#155`
- native workspace browser harness or wrapper verification is red
- the bundle-scope check no longer stays isolated

## Decision Rule

- if `#155` is green on its own workspace scope, merge it
- do **not** wait for `#157` or `#158`
- only treat `#156` as relevant if the reviewer believes the router follow-up
  should land before or alongside the main branch
- otherwise keep `#156`, `#157`, and `#158` as separate merge decisions

## Fast References

- `docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md`
- `docs/PR_MERGE_READINESS_NOTE_20260409.md`
- `docs/PR_REVIEWER_ASSIGNMENT_PLAN_20260409.md`
- `docs/PR_TRIAGE_SUMMARY_20260409.md`
- `docs/SPLIT_PR_REVIEW_ORDER_20260409.md`

## One-Line Operator Rule

If `#155` is green on native workspace scope and the reviewer is not asking to
widen it, merge `#155` and keep the split PRs separate.
