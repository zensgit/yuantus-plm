# DEV / Verification — New Cycle Topic Selection + Backlog Triage Closeout (2026-04-26)

## 1. Goal

Close the "what's next?" question after the recent closeout chain (PRs #398
single-PR worktree closeout, #399 approvals follow-up, #400 doc-index
contract discipline note). Two related axes: new-cycle topic selection,
and ordering of the residual backlog. This MD does **not** open an
implementation branch; it is a planning artifact only.

Companion to (and delta over):

- `docs/DEV_AND_VERIFICATION_BACKLOG_TRIAGE_20260422.md`
- `docs/DEV_AND_VERIFICATION_NEXT_CYCLE_CLOSEOUT_AND_REMAINING_WORK_20260423.md`
- `docs/DEV_AND_VERIFICATION_NEW_CYCLE_INTAKE_AND_WORKLOAD_20260423.md`

## 2. New-Cycle Topic Decision

**Decision: do not start another implementation cycle by default.**

The post-04-23 intake doc's §4 sequencing applies as-is. No external trigger
(customer pull signal, ops pilot owner, named operator window, hotspot
evidence) has materialized since 04-23. The recommended next step is to
collect external signal or wait, not to open a new bounded taskbook.

## 3. Backlog Delta Since 2026-04-23

Three observations that change the picture relative to the 04-23 intake:

### 3.1 Compatibility-shell cleanup — disposition unchanged, surface area grew

Status update on item §5 row "Remove zero-route compatibility shells" of
`DEV_AND_VERIFICATION_NEXT_CYCLE_CLOSEOUT_AND_REMAINING_WORK_20260423.md`:

- `file_router.py` — promoted to "shell present, unregistered" by PR #387.
- `approvals_router.py` — promoted to "shell present, unregistered" in
  commit `55ffae4`, documented in
  `DEV_AND_VERIFICATION_APPROVALS_ROUTER_DECOMPOSITION_CLOSEOUT_UNREGISTRATION_20260425.md`.
- Other `*_router.py` modules with zero `@router.*` decorators (still
  registered in `app.py`): `bom_router.py` (3 LOC), `eco_router.py` (10 LOC
  re-export shim), and others under the post-04-23 router decompositions
  (`box_router`, `cutted_parts_router`, `version_router`, `quality_router`,
  `subcontracting_router`, `maintenance_router`, `report_router`,
  `document_sync_router`).

Disposition still **dormant**: ROI is low; no functional change. A future
cycle could standardize all remaining shells to "shell + unregistered" or
delete them outright. Estimated effort: 2–3 days for ~7–10 router families,
depending on how many tests pin the legacy module path.

### 3.2 Service extraction — precedent set, no new hotspot named

CadImportService extraction (PR #379) sets the precedent for service-layer
splits. Specific candidates **only** if hotspot evidence emerges:

- `BOMService` — large; covers compare / tree / rollup / obsolete / where-used.
- `DocumentSyncService` — multi-mode (analytics / reconciliation / replay /
  drift / lineage / retention / freshness).

Disposition still **dormant**. Do not split for cleanliness alone; require
specific review pain, perf finding, or contract gap.

### 3.3 Closeout-tooling discoverability — covered by docs, not code

PR #399's local-snapshot gap motivated PR #400's
`DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md`. CI already
runs the full doc-index trio; a `--verification-commands` extension to
`scripts/print_current_worktree_closeout_commands.sh` was considered and
deferred as non-goal because CI is already correct and the discipline rule
is now discoverable.

Disposition: **dormant**, low priority unless a similar review-cycle gap
recurs.

## 4. Priority Ordering When A Trigger Appears

If multiple triggers materialize in the same window, address in this
order. Each row carries its own gating trigger; do not start without it.

| Order | Item | Effort | Required trigger |
| ---: | --- | ---: | --- |
| 1 | Scheduler production rehearsal | 2–5 days + ops window | Pilot owner + pilot environment + monitoring/rollback owner |
| 2 | Compatibility-shell standardization (~7–10 families) | 2–3 days | Codebase-cleanup priority elevated explicitly |
| 3 | BOMService extraction | 1–3 days | Hotspot evidence (review pain, perf, contract gap) |
| 4 | DocumentSyncService extraction (per slice) | 1–3 days each | Same as (3) |
| 5 | Closeout helper `--verification-commands` mode | 0.5 day | Recurrence of the PR #399-style local-snapshot gap |
| 6 | UI work (BOM Diff / CAD Viewer / approvals) | 1–3+ weeks | Customer or stakeholder pull signal |
| 7 | Shared-dev `142` readonly observation rerun | 0.5 day per run | Explicit credentials + execution window |

Items deleted from this cycle's scope (do not re-surface here): MES /
sales / procurement expansion.

## 5. Stop Conditions

Do **not** open implementation PRs when any of these hold:

- No owner is named.
- No target user or operator is identified.
- No acceptance criteria are written.
- The change mixes runtime behavior, UI, scheduler activation, and
  shared-dev mutation.
- The work is only adding more planning around an already blocked item.

These are unchanged from `DEV_AND_VERIFICATION_NEW_CYCLE_INTAKE_AND_WORKLOAD_20260423.md` §6.

## 6. Verification

```bash
git diff --check

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected: clean + 4 passed.

## 7. Files Changed

- `docs/DEV_AND_VERIFICATION_NEW_CYCLE_BACKLOG_TRIAGE_20260426.md` (this MD)
- `docs/DELIVERY_DOC_INDEX.md` (entry for this MD, alphabetically positioned
  before the existing `NEW_CYCLE_INTAKE_AND_WORKLOAD_20260423` entry —
  `BACKLOG` < `INTAKE`)

## 8. Non-Goals

- No new implementation branch.
- No code, schema, runtime, or CI changes.
- No scheduler enablement.
- No shared-dev `142` mutation.
- No new contract test.
- No retroactive edit of the 04-22 / 04-23 planning MDs (they remain
  canonical for their dates).

## 9. Recommended Next Operating Mode

Mirror `NEXT_CYCLE_CLOSEOUT_AND_REMAINING_WORK_20260423.md` §6 verbatim:

1. Keep `main` stable.
2. Run only focused maintenance checks after adjacent changes.
3. Collect external signal from a real user, operator, or deployment.
4. Open a new cycle only when there is a bounded trigger.
5. For any new cycle, require a taskbook, DEV_AND_VERIFICATION MD, index
   registration, focused tests, and post-merge validation.
