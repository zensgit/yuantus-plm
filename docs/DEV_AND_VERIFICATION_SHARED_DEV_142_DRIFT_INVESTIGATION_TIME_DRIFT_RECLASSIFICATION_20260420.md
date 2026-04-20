# DEV_AND_VERIFICATION_SHARED_DEV_142_DRIFT_INVESTIGATION_TIME_DRIFT_RECLASSIFICATION_20260420

## Context

- Date: 2026-04-20
- Base branch: `main` at `9d17489588ff1540b16ed3d328b1050c85384226`
- Scope: refine `shared-dev 142 drift-investigation` so it can distinguish generic `state-drift` from deadline-driven `time-drift`
- Trigger: the first real `142` drift-investigation run succeeded technically but only concluded `state-drift`, even though the artifact diff already suggested that one approval simply crossed its existing deadline

## Problem

`render_p2_shared_dev_142_drift_investigation.py` previously classified all same-population metric drift as `state-drift`.

That was too coarse for the real `142` evidence pack:

- `added_approval_ids=[]`
- `removed_approval_ids=[]`
- one approval moved from:
  - `is_overdue=false`
  - `hours_overdue=null`
- to:
  - `is_overdue=true`
  - `hours_overdue>0`
- the other changed approvals only accumulated more `hours_overdue`

This is materially different from a likely write-path mutation.

## Change

Updated `scripts/render_p2_shared_dev_142_drift_investigation.py` to:

1. load baseline/current `items.json` when the drift-audit payload includes `baseline_dir` and `current_dir`
2. compute entity-level approval deltas instead of relying only on summary metrics
3. detect `time-drift` when:
   - approval membership is unchanged
   - changed fields stay within `is_overdue` / `hours_overdue`
   - at least one approval crosses from pending to overdue on the same stored deadline
4. emit:
   - `classification: time-drift`
   - `likely_cause.kind: deadline-rollover`
   - `time_drift_approval_ids`
   - `approval_change_rows`
5. update the investigation checklist so operators handle `deadline-rollover` separately from write-driven `state-drift`

## Files

- `scripts/render_p2_shared_dev_142_drift_investigation.py`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py`
- `docs/P2_SHARED_DEV_142_DRIFT_INVESTIGATION_CHECKLIST.md`

## Local Verification

```bash
python3 -m py_compile scripts/render_p2_shared_dev_142_drift_investigation.py
bash -n scripts/run_p2_shared_dev_142_drift_investigation.sh
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Result:

- `34 passed`

Notable test coverage:

- existing generic same-population drift still stays `state-drift`
- new synthetic deadline-rollover fixture now reclassifies to `time-drift`

## Real Shared-dev 142 Verification

Executed from the clean worktree with the existing local observation env:

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation
```

Real runtime summary:

- `SUMMARY_HTTP_STATUS=200`
- `READONLY_EXIT_STATUS=1`
- `DRIFT_AUDIT_EXIT_STATUS=1`
- `INVESTIGATION_VERDICT=FAIL`
- `INVESTIGATION_CLASSIFICATION=time-drift`

Result directory:

- `tmp/p2-shared-dev-142-drift-investigation-20260420-225119/`

Key investigation output:

- `tmp/p2-shared-dev-142-drift-investigation-20260420-225119/DRIFT_INVESTIGATION.md`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-225119/drift_investigation.json`

Key findings now rendered explicitly:

- `likely_cause.kind = deadline-rollover`
- `time_drift_approval_ids = ["022d7b29-6183-4941-b02e-ee647efef9ab"]`
- `pending_count: 2 -> 1`
- `overdue_count: 3 -> 4`
- `total_anomalies: 2 -> 3`
- `overdue_not_escalated: 1 -> 2`
- approval membership still unchanged:
  - `added_approval_ids=[]`
  - `removed_approval_ids=[]`

The changed approval table now makes the underlying cause visible:

- `eco-pending`
  - same `approval_deadline`
  - `is_overdue: false -> true`
  - `hours_overdue: null -> 9.26...`
- existing overdue approvals only increased `hours_overdue`

## Conclusion

The `142` drift line is now classified more precisely:

- before: `state-drift`
- after this remediation: `time-drift`

That does **not** make the readonly guard pass, but it does materially improve the operational decision:

- this drift currently looks like baseline aging across a real deadline
- it is no longer best described as an unexplained write-driven state mutation

The next decision is operational:

1. accept the baseline as time-sensitive and refreeze it
2. or redesign the readonly baseline so it does not age across the observation window
