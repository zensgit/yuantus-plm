# DEV_AND_VERIFICATION_SHARED_DEV_142_DRIFT_AUDIT_RUNTIME_REMEDIATION_20260420

## Context

- Date: 2026-04-20
- Scope: harden `scripts/run_p2_shared_dev_142_drift_audit.sh` after first real shared-dev 142 execution
- Trigger: the first live `drift-audit` run reached the real `142` environment, completed precheck and readonly rerun, but exited before writing top-level `DRIFT_AUDIT.md` / `drift_audit.json`

## Problem

`run_p2_shared_dev_142_drift_audit.sh` called `run_p2_shared_dev_142_readonly_rerun.sh` under `set -e`.  
When the nested readonly compare/eval returned non-zero because drift was real, the wrapper exited immediately, so the top-level drift audit renderer never ran.

This produced:

- `current/OBSERVATION_RESULT.md`
- `current/OBSERVATION_DIFF.md`
- `current/OBSERVATION_EVAL.md`

but failed to produce:

- `DRIFT_AUDIT.md`
- `drift_audit.json`

That behavior defeated the purpose of the helper: drift investigation must still emit a focused audit artifact even when readonly stability fails.

## Change

Updated `scripts/run_p2_shared_dev_142_drift_audit.sh` so it now:

1. captures the nested readonly rerun exit code instead of exiting immediately
2. prints a clear stderr note when readonly rerun fails
3. always renders:
   - `DRIFT_AUDIT.md`
   - `drift_audit.json`
4. prints:
   - `READONLY_EXIT_STATUS=<n>`
   - `DRIFT_VERDICT=<PASS|FAIL>`
5. preserves non-zero exit semantics after rendering:
   - returns the readonly rerun failure code when readonly failed
   - otherwise returns `1` when drift verdict is `FAIL`

## Tests

### Local syntax + targeted pytest

```bash
bash -n scripts/run_p2_shared_dev_142_drift_audit.sh
bash -n scripts/print_p2_shared_dev_142_drift_audit_commands.sh
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
```

### Dedicated runtime regression

Added a new regression case in:

- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py`

Coverage:

- stub nested readonly rerun writes current artifacts and exits `1`
- drift wrapper still writes:
  - `DRIFT_AUDIT.md`
  - `drift_audit.json`
- wrapper preserves non-zero exit
- stdout/stderr expose:
  - continuation notice
  - readonly exit status
  - drift verdict

## Result

- drift-audit no longer drops top-level audit artifacts when real readonly drift exists
- operators can now use the helper for investigation before any readonly refreeze decision
