# Scheduler Production Decision Gate - Development And Verification

Date: 2026-04-23

## 1. Goal

Make an explicit go / no-go decision for scheduler production enablement.

This document closes the current scheduler planning loop. It does not enable the scheduler, does not add another scheduler operations wrapper, and does not run shared-dev `142` scheduler activation.

## 2. Decision

Verdict: `NO-GO` for production scheduler rehearsal now.

Disposition: scheduler enters `default-off maintenance`.

This means:

- `SCHEDULER_ENABLED` remains default `false`;
- shared-dev `142` remains readonly / no-op for scheduler unless explicitly authorized;
- no new scheduler ops PR should be opened without a real pull signal;
- existing scheduler foundation, dry-run, local activation suite, and three consumers remain available for local validation and future pilot preparation.

## 3. Gate Criteria

| Gate input | Required for go | Current evidence | Result |
| --- | --- | --- | --- |
| Pilot owner | A named person or team commits to running scheduler rehearsal | No named scheduler pilot owner is present in `DEV_AND_VERIFICATION_EXTERNAL_SIGNAL_COLLECTION_20260422.md` | Missing |
| Pilot environment | A production-like environment is authorized for scheduler rehearsal | Shared-dev `142` has readonly/no-op evidence only; local activation suite is not production-like | Missing |
| Operations commitment | Monitoring, rollback, and incident ownership are assigned | No operations owner or rollback window has been provided | Missing |
| Technical readiness | Dry-run, default-off guard, local activation, and consumer handlers exist | Scheduler foundation, dry-run preflight, audit retention, ECO escalation, BOM-to-MBOM consumer, jobs readback, and local activation suite are documented | Present |
| Safety boundary | Decision PR does not enable production or shared-dev scheduler | This PR is documentation-only | Present |

Decision rule: all three non-technical inputs must be present before a production rehearsal taskbook is justified. Because the first three inputs are missing, the correct decision is no-go.

## 4. Evidence Reviewed

- `docs/DEV_AND_VERIFICATION_LIGHTWEIGHT_SCHEDULER_FOUNDATION_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_DRY_RUN_PREFLIGHT_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_DRY_RUN_PREFLIGHT_HELPER_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_AUDIT_RETENTION_ACTIVATION_RUNBOOK_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_ECO_ESCALATION_ACTIVATION_RUNBOOK_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_BOM_TO_MBOM_HANDLER_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_BOM_TO_MBOM_ACTIVATION_RUNBOOK_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_JOBS_API_READBACK_SMOKE_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_LOCAL_ACTIVATION_SUITE_20260421.md`
- `docs/DEV_AND_VERIFICATION_SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT_20260421.md`
- `docs/DEV_AND_VERIFICATION_BACKLOG_TRIAGE_20260422.md`
- `docs/DEV_AND_VERIFICATION_EXTERNAL_SIGNAL_COLLECTION_20260422.md`

## 5. What Remains Allowed

Allowed while in `default-off maintenance`:

- fixing scheduler bugs discovered by existing tests;
- keeping existing contract tests and docs current when adjacent code moves;
- running local activation suite after scheduler-related code changes;
- running dry-run preflight against an authorized environment;
- preparing a new rehearsal taskbook only after the reopen criteria in section 7 are met.

Not allowed without reopening this gate:

- enabling scheduler on production;
- enabling scheduler on shared-dev `142`;
- adding another scheduler consumer by default;
- adding more activation wrappers as a substitute for a pilot commitment;
- opening a production rehearsal PR without named owner, environment, monitoring, and rollback evidence.

## 6. Current Scheduler Assets

| Area | Current status |
| --- | --- |
| Foundation | Lightweight scheduler enqueues into the existing `meta_conversion_jobs` queue |
| Global safety | `SCHEDULER_ENABLED=false` by default |
| Dry-run | `yuantus scheduler --dry-run` and helper script exist |
| Consumer 1 | `audit_retention_prune` local activation smoke exists |
| Consumer 2 | `eco_approval_escalation` local activation smoke exists |
| Consumer 3 | `bom_to_mbom_sync` local activation smoke exists |
| Readback | Scheduler job can be read through jobs API smoke |
| Suite | Local activation suite and renderer exist |
| Shared-dev | Existing evidence is readonly/no-op/default-off only |

## 7. Reopen Criteria

Open a new scheduler production rehearsal taskbook only when all of these are true:

- a named pilot owner is recorded;
- a target environment is approved for scheduler rehearsal;
- an operations owner accepts monitoring and rollback responsibility;
- dry-run preflight is run against the target environment and archived;
- rollback command and expected disabled state are documented;
- a time-boxed rehearsal window is approved.

If these are not present, keep scheduler in `default-off maintenance`.

## 8. Files Changed

- `docs/DEV_AND_VERIFICATION_SCHEDULER_PRODUCTION_DECISION_GATE_20260423.md`
- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 9. Verification

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

## 10. Explicit Non-Goals

- No runtime scheduler changes.
- No new scheduler settings.
- No schema or migration changes.
- No shared-dev `142` activation.
- No production scheduler enablement.
- No local activation suite rerun, because this decision gate changes no scheduler runtime behavior.

