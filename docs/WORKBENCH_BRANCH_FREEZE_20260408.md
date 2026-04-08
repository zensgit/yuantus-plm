# metasheet2-plm-workbench Branch Freeze Notice

## Decision (2026-04-08)

The `codex/plm-workbench-collab-20260312` branch in `zensgit/metasheet2`
(checked out at `/Users/huazhou/Downloads/Github/metasheet2-plm-workbench`)
is **frozen** as of this date.

No new work should be started on this branch. Existing changes should be
reviewed and merged back to mainline via a dedicated PR — not cherry-picked
piecemeal.

## Why freeze now

Wave 1 + Wave 1.5 of the Pact-First integration plan has just been
completed on the **mainline** branch (`codex/approval-bridge-plm-phase1-20260404`).
All 6 P0 pact interactions pass end-to-end. Introducing workbench changes
before push would risk destabilizing the safety net.

The workbench branch is 384 commits ahead of `origin/main` — too far
ahead for safe cherry-picking. A proper merge review is required.

## Precise PLMAdapter.ts differences (vs mainline)

The PLMAdapter divergence is contained in one commit:

  `2dff0263f fix(plm-workbench): align approval version contracts`

Changes in that commit:

| Area | Mainline state | Workbench state | Notes |
|---|---|---|---|
| `ApprovalRequest.version` field | Present (optional number) | **Removed** | Response-side version removed |
| `YuantusEco.version` field | Present (number or string) | **Removed** | Same rationale |
| `mapYuantusEcoApproval` version normalization | Present (~6 lines) | **Removed** | Coupled with field removal |
| `getApprovalById()` method | Present (38 lines) | **Removed** | Replacement pattern unclear |
| `approveApproval()` signature | `(id, comment?)` | `(id, version, comment?)` | Optimistic locking added |
| `rejectApproval()` signature | `(id, comment)` | `(id, version, comment)` | Same |
| `approve/reject` request payload | `{ comment }` | `{ version, comment }` | version sent to Yuantus |

The net change is: workbench removes response-side version tracking and
adds request-side optimistic locking. This is a coherent but invasive
design change that requires review.

## Impact on Pact contracts

The Wave 1 P0 pact does **not** cover approve/reject (those are Wave 2
endpoints). Therefore the workbench PLMAdapter changes have no impact on
the current pact safety net.

When Wave 2 pact work begins:
- `POST /api/v1/eco/{id}/approve` should declare `version` as **optional**
  in the request body (Matchers.like, field may or may not be present)
- This allows both the mainline signature (no version) and the workbench
  signature (with version) to pass the same pact
- When the merge PR lands, the pact can be tightened to require version

## Recommended merge path

1. **Do not cherry-pick** from the workbench branch to mainline. The
   changes are too intertwined (17 files, design-level decisions).
2. **Create a dedicated merge PR** from `codex/plm-workbench-collab-20260312`
   to mainline that:
   - Reviews the removal of `getApprovalById()` — is there a replacement?
   - Reviews the removal of response-side `version` — why was it removed?
   - Accepts the addition of request-side `version` for optimistic locking
   - Resolves the 384-commit divergence (likely a large squash-merge)
3. **Only after the merge PR is reviewed and landed**, consider closing
   the workbench worktree.
4. **Do not start new features on this branch** while it is frozen.

## Downstream notification

If codex (or any other agent) attempts to commit to this branch, the
freeze should be flagged. The freeze can be lifted once the merge PR
described above is complete.

## Cross-references

- `docs/METASHEET_REPO_SOURCE_OF_TRUTH_INVESTIGATION_20260407.md` — original source-of-truth decision
- `docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md` — Wave 2 approve/reject endpoint list
- `docs/PACT_DELIBERATE_BREAK_EXPERIMENT_20260408.md` — Wave 1 proof
