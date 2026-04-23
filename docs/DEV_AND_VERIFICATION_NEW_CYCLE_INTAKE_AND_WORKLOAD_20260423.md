# New Cycle Intake And Workload - Development And Verification

Date: 2026-04-23

## 1. Goal

Define what can happen after `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` is complete.

This document separates two questions that should not be mixed:

- Current plan completion: finished, with `0` plan-defined implementation work remaining.
- Broader roadmap work: only start as a new cycle when a concrete trigger exists.

This is a documentation-only intake record. It does not add runtime code, schema, tests, UI, scheduler activation, or shared-dev writes.

## 2. Current Plan Workload

| Scope | Status | Remaining workload |
| --- | --- | ---: |
| `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md` | Closed by PR #381 | 0 days |
| P0 closeout validation | Complete | 0 days |
| P0.5 backlog triage | Complete | 0 days |
| External signal collection | Complete for the cycle | 0 days |
| P1 BOM router decomposition | Complete | 0 days |
| P2 UOM transformation rules granularity | Complete | 0 days |
| P3 CadImportService extraction | Complete | 0 days |
| P4 scheduler production decision gate | Complete | 0 days |

Answer: we are not "close" to completing the current plan; it is already complete.

## 3. New Cycle Candidate Table

| Candidate | Type | Estimated effort | Trigger | Recommendation |
| --- | --- | ---: | --- | --- |
| New cycle intake with named owner | Planning gate | 0.5 day | User or stakeholder chooses a target theme | Do first before new implementation |
| Shared-dev `142` readonly observation rerun | Maintenance evidence | 0.5 day per run | Explicit credentials and execution window | Optional; no bootstrap |
| Zero-route compatibility shell cleanup | Architecture cleanup | 0.5-1 day per router family | Compatibility cleanup selected and contracts updated | Low ROI; defer unless cleanliness is the goal |
| Additional service extraction | Architecture cleanup | 1-3 days per service | Hotspot evidence or repeated review pain | Pick one service only per PR |
| Scheduler production rehearsal | Operations rollout | 2-5 days plus ops window | Pilot owner, approved environment, monitoring owner, rollback owner | Blocked; keep default-off |
| BOM Diff UI / CAD Viewer / Approval UI | Product UI | 1-3+ weeks depending scope | Customer or stakeholder pull signal | Do not start without UX/product scope |
| MES / sales / procurement expansion | New business scope | Not estimated | Roadmap approval and domain owner | Out of current backend scope |

## 4. Recommended Immediate Path

Do not start another implementation branch by default.

Recommended next step:

1. Ask for one concrete new-cycle target.
2. Write a bounded taskbook for that target.
3. Let Claude implement only after the taskbook is reviewed.
4. Keep Codex on review, focused regression, PR merge validation, and DEV_AND_VERIFICATION closeout.

If a target must be chosen without new external signal, the least risky ordering is:

1. New cycle intake taskbook.
2. Optional `142` readonly rerun if credentials and window are already available.
3. One service extraction only if a specific hotspot is named.
4. Compatibility shell cleanup only if the team wants repo cleanliness over product value.

## 5. Workload Bands

| Band | Meaning | Examples |
| --- | --- | --- |
| `0 days` | Already complete in the current plan | P0-P4 current plan work |
| `0.5 day` | Documentation, readonly rerun, or small verification-only work | Intake doc, 142 readonly rerun |
| `0.5-1 day` | Very small cleanup with contracts | Remove one zero-route compatibility shell |
| `1-3 days` | Bounded backend implementation | One service extraction, one focused refactor |
| `2-5 days + ops window` | Operational rollout | Scheduler production rehearsal |
| `1-3+ weeks` | Product/UI scope | BOM Diff UI, CAD Viewer, Approval UI |

## 6. Stop Conditions

Do not open implementation PRs when any of these are true:

- no owner is named;
- no target user or operator is identified;
- no acceptance criteria are written;
- the change mixes runtime behavior, UI, scheduler activation, and shared-dev mutation;
- the work is only adding more planning around an already blocked item.

## 7. Files Changed

- `docs/DEV_AND_VERIFICATION_NEW_CYCLE_INTAKE_AND_WORKLOAD_20260423.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 8. Verification

Commands:

```bash
git diff --check

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- `git diff --check`: pass
- doc-index contract tests: pass

## 9. Non-Goals

- No code implementation.
- No scheduler enablement.
- No shared-dev `142` write operation.
- No first-run bootstrap.
- No UI work.
- No new production rollout.

