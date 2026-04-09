# PR Reviewer Assignment Plan

Date: `2026-04-09`
Repository: `zensgit/yuantus-plm`

This note gives the shortest reviewer-assignment and mention plan across the
main native workspace PR and the three extracted residual split PRs.

## Constraint

- there is no checked-in `CODEOWNERS` file in this repository
- recent ownership on the touched files is effectively collapsed to `zensgit`
- reviewer assignment should therefore be concern-based, not handle-based

## Suggested Reviewer Lanes

1. Native workspace / browser-harness reviewer
   Owns `#155`.
2. Router / runtime reviewer
   Owns `#156` after `#155`.
3. Doc-governance reviewer
   Owns `#157`.
4. Product-doc reviewer
   Owns `#158`.

## Shortest Assignment Order

1. Assign `#155` first.
   This is the primary product review thread.
2. Assign `#156` next.
   This is the only follow-up PR that changes runtime behavior and tests.
3. Assign `#157` and `#158` in parallel after `#156`, or independently if the
   reviewers only care about doc hygiene.

## Mention Plan

### `#155`

Use one reviewer who can cover:

- API route wiring
- workspace runtime behavior
- browser harness / Playwright wrappers

Paste-ready mention:

```text
Please take `#155` first. Keep review scope on native workspace / browser-harness wiring only.
Use `docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md` and `docs/PR_TRIAGE_SUMMARY_20260409.md`.
```

### `#156`

Use one reviewer who can cover:

- router prefix behavior
- routing 404 handling
- router tests

Paste-ready mention:

```text
Please take `#156` after `#155`. This is the first code-facing follow-up PR and should stay separate from the main workspace review.
```

### `#157`

Use one reviewer who can cover:

- governance/operator docs
- launch and handoff guidance hygiene

Paste-ready mention:

```text
Please review `#157` as a doc-only follow-up. It can be reviewed in parallel with `#158` once `#156` routing is clear.
```

### `#158`

Use one reviewer who can cover:

- product strategy docs
- SKU/workflow ownership docs

Paste-ready mention:

```text
Please review `#158` as a doc-only follow-up. It can be reviewed in parallel with `#157` once `#156` routing is clear.
```

## Fallback If Only One Reviewer Is Available

1. Review `#155`
2. Review `#156`
3. Review `#157`
4. Review `#158`

## References

- `docs/PR_MERGE_READINESS_NOTE_20260409.md`
- `docs/PR_TRIAGE_SUMMARY_20260409.md`
- `docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md`
- `docs/SPLIT_PR_REVIEW_ORDER_20260409.md`
- `docs/SPLIT_BRANCHES_SUMMARY_20260409.md`
