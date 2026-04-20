# DEV_AND_VERIFICATION_SHARED_DEV_142_DRIFT_INVESTIGATION_HELPER_20260420

## Context

- Date: 2026-04-20
- Scope: add a dedicated shared-dev 142 drift investigation helper on top of the merged readonly guard and drift-audit flow

## Why

`drift-audit` already answers one question:

- what changed between the frozen readonly baseline and the current 142 observation surface

But after the first real 142 drift runs, there was still one operator gap:

- the next step was split across multiple files and scripts
- evidence paths were easy to lose
- candidate write sources were not collected in a single place

This follow-up closes that gap by adding a repeatable evidence-pack wrapper before any readonly refreeze decision.

## Deliverables

### New scripts

- `scripts/run_p2_shared_dev_142_drift_investigation.sh`
- `scripts/print_p2_shared_dev_142_drift_investigation_commands.sh`
- `scripts/render_p2_shared_dev_142_drift_investigation.py`

### New docs

- `docs/P2_SHARED_DEV_142_DRIFT_INVESTIGATION_CHECKLIST.md`

## Behavior

The new wrapper:

1. runs `run_p2_shared_dev_142_drift_audit.sh` into a nested `drift-audit/` directory
2. keeps the nested drift failure semantics
3. renders:
   - `DRIFT_INVESTIGATION.md`
   - `drift_investigation.json`
4. classifies the drift as:
   - `no-drift`
   - `state-drift`
   - `membership-drift`
   - `mixed-drift`
5. records a fixed evidence manifest plus a static list of likely write-source paths

This helper still does not:

- mutate the baseline
- auto-refreeze
- perform any write-side smoke

## Repo entrypoint integration

`scripts/run_p2_shared_dev_142_entrypoint.sh` now exposes:

- `drift-investigation`
- `print-investigation-commands`

That keeps all shared-dev 142 readonly triage paths under one selector.

This follow-up also closes the last operator handoff gap:

- `docs/P2_SHARED_DEV_142_DRIFT_AUDIT_CHECKLIST.md` now explicitly hands off to
  - `docs/P2_SHARED_DEV_142_DRIFT_INVESTIGATION_CHECKLIST.md`
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation`
  - `bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-investigation-commands`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md` now points workflow operators at the same investigation path once readonly drift is confirmed

## Verification

### Syntax

```bash
bash -n scripts/run_p2_shared_dev_142_drift_investigation.sh
bash -n scripts/print_p2_shared_dev_142_drift_investigation_commands.sh
python3 -m py_compile scripts/render_p2_shared_dev_142_drift_investigation.py
```

### Targeted contracts

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Result:

- `53 passed`

### Expected runtime semantics

- if nested drift-audit fails because real drift exists, the investigation wrapper still writes:
  - `DRIFT_INVESTIGATION.md`
  - `drift_investigation.json`
- the wrapper keeps non-zero drift semantics, so automation still sees investigation-needed status
