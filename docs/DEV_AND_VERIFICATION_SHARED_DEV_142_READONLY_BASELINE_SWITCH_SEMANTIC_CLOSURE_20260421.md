# DEV_AND_VERIFICATION_SHARED_DEV_142_READONLY_BASELINE_SWITCH_SEMANTIC_CLOSURE_20260421

## Context

- Date: 2026-04-21
- Base branch: `main` at `f84d79cf364961250c536006474f17bb753c665c`
- Goal: safely promote `shared-dev-142-readonly-20260421` as the official tracked baseline without immediately breaking readonly rerun semantics

## Problem

`#302` produced a valid overdue-only readonly proposal pack, but a naive baseline label/dir switch was unsafe.

Before this change:

- the current live shared-dev 142 surface still contained one future-deadline pending approval
- the proposed tracked baseline intentionally excluded that pending approval
- official readonly compare/eval still compared the raw live current directly against the tracked baseline

That meant:

- switching only the tracked label from `shared-dev-142-readonly-20260419` to `shared-dev-142-readonly-20260421`
- without changing the official compare path

would make official readonly rerun fail again immediately.

## Change

This follow-up closes that semantic gap.

### 1. Official tracked baseline switched to `20260421`

Added the new tracked baseline tree:

- `artifacts/p2-observation/shared-dev-142-readonly-20260421/`

Sanitized it for tracked use:

- `README.txt` now identifies it as the official tracked baseline, not a proposal/candidate scratch dir
- `OBSERVATION_RESULT.md` and `OBSERVATION_EVAL.md` no longer point at private proposal tmp paths
- added `baseline_policy.json`

`baseline_policy.json` now defines the official policy:

```json
{
  "kind": "overdue-only-stable",
  "summary": "Official shared-dev 142 readonly compare/eval excludes pending approvals from the live current surface before diff and evaluation.",
  "tracked_label": "shared-dev-142-readonly-20260421"
}
```

### 2. Added stable-current transform for official readonly compare/eval

New helper:

- `scripts/render_p2_shared_dev_142_stable_current.py`

It:

- reads raw current observation artifacts
- excludes pending approvals from the live current surface
- writes an effective stable current pack
- renders:
  - `OBSERVATION_RESULT.md`
  - `OBSERVATION_EVAL.md`
  - `STABLE_CURRENT_TRANSFORM.md`
  - `stable_current_transform.json`

### 3. Updated official readonly/runtime paths

Updated scripts:

- `scripts/run_p2_shared_dev_142_readonly_rerun.sh`
- `scripts/run_p2_shared_dev_142_workflow_readonly_check.sh`
- `scripts/run_p2_shared_dev_142_drift_audit.sh`
- `scripts/run_p2_shared_dev_142_drift_investigation.sh`
- `scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh`
- `scripts/print_p2_shared_dev_142_drift_audit_commands.sh`
- `scripts/print_p2_shared_dev_142_drift_investigation_commands.sh`
- `scripts/render_p2_shared_dev_142_drift_audit.py`
- `scripts/render_p2_shared_dev_142_refreeze_proposal.py`

Behavior now:

- when `baseline_policy.json.kind == overdue-only-stable`
- official readonly rerun captures:
  - raw current under `raw-current/`
  - stable effective current at the top-level output dir
- readonly diff/eval run against the stable current, not the raw current

That preserves:

- raw live evidence
- stable official compare semantics

### 4. Updated current operator docs/checklists

Updated current guidance:

- `docs/P2_SHARED_DEV_142_DRIFT_AUDIT_CHECKLIST.md`
- `docs/P2_SHARED_DEV_142_DRIFT_INVESTIGATION_CHECKLIST.md`
- `docs/P2_SHARED_DEV_142_READONLY_REFREEZE_CANDIDATE_CHECKLIST.md`
- `docs/P2_SHARED_DEV_142_READONLY_REFREEZE_READINESS_CHECKLIST.md`

Historical dated execution records were intentionally left as historical evidence.

### 5. Updated contracts/tests

Updated:

- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`
- `src/yuantus/meta_engine/tests/test_shared_dev_142_readonly_guard_workflow_contracts.py`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py`

Added integration coverage for:

- stable-current transform helper
- readonly rerun using the overdue-only tracked baseline policy

## Local Verification

### Syntax / compile

```bash
bash -n scripts/run_p2_shared_dev_142_readonly_rerun.sh
bash -n scripts/run_p2_shared_dev_142_workflow_readonly_check.sh
bash -n scripts/run_p2_shared_dev_142_drift_audit.sh
bash -n scripts/run_p2_shared_dev_142_drift_investigation.sh
python3 -m py_compile \
  scripts/render_p2_shared_dev_142_stable_current.py \
  scripts/render_p2_shared_dev_142_drift_audit.py \
  scripts/render_p2_shared_dev_142_refreeze_proposal.py
```

### Targeted tests

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  -k "stable_current or readonly_rerun_uses_stable_current_for_overdue_only_policy or refreeze_proposal_materializes_tracked_candidate_pack or drift_audit_still_renders_when_readonly_rerun_fails"

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_shared_dev_142_readonly_guard_workflow_contracts.py
```

Observed:

- targeted wrapper suite: `4 passed`
- contracts/discoverability/syntax suite: `37 passed`

## Real Shared-dev 142 Verification

Executed from clean worktree:

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit
```

### Readonly rerun result

Artifacts:

- `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-083915-precheck/OBSERVATION_PRECHECK.md`
- `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-083915/raw-current/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-083915/STABLE_CURRENT_TRANSFORM.md`
- `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-083915/stable_current_transform.json`
- `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-083915/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-083915/OBSERVATION_DIFF.md`
- `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-083915/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-observation-142-readonly-rerun-20260421-083915.tar.gz`

Observed:

- `SUMMARY_HTTP_STATUS=200`
- `BASELINE_POLICY_KIND=overdue-only-stable`
- raw current counts:
  - `items=5`
  - `pending=1`
  - `overdue=4`
  - `escalated=1`
  - `anomalies=3`
- stable current counts:
  - `items=4`
  - `pending=0`
  - `overdue=4`
  - `escalated=1`
  - `anomalies=3`
- excluded pending approval:
  - `af1a2dc4-7d73-4d1d-aabb-acdde37abea8`
- `OBSERVATION_EVAL.md` verdict:
  - `PASS`
  - `20/20 passed`

### Drift audit result

Artifacts:

- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/current-precheck/OBSERVATION_PRECHECK.md`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/current/raw-current/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/current/STABLE_CURRENT_TRANSFORM.md`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/current/stable_current_transform.json`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/current/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/current/OBSERVATION_DIFF.md`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/current/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/DRIFT_AUDIT.md`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915/drift_audit.json`
- `tmp/p2-shared-dev-142-drift-audit-20260421-083915.tar.gz`

Observed:

- `READONLY_EXIT_STATUS=0`
- `DRIFT_VERDICT=PASS`
- `changed_metrics=[]`
- `added_approval_ids=[]`
- `removed_approval_ids=[]`

This confirms the official drift path now compares the stable current slice against the overdue-only tracked baseline, instead of constantly re-failing on the expected future pending item.

## Conclusion

This change safely closes the gap between:

- the accepted `20260421` overdue-only tracked baseline
- and the official shared-dev 142 readonly compare/eval runtime

At this point:

- official readonly rerun is green again on real `142`
- official drift audit is green again on real `142`
- raw current evidence is still preserved under `raw-current/`

The baseline switch is therefore semantically closed, not just relabeled.
