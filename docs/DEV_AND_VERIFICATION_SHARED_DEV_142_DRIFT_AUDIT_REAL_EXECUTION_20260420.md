# DEV_AND_VERIFICATION_SHARED_DEV_142_DRIFT_AUDIT_REAL_EXECUTION_20260420

## Context

- Date: 2026-04-20
- Scope: run the merged shared-dev 142 `drift-audit` entrypoint against the real `142` environment
- Goal: close the shared-dev 142 observation line with a real operator-grade drift investigation run, not only local unit coverage

## Entry Point

Executed from repo root on post-merge `main` content:

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit
```

Env source:

- `~/.config/yuantus/p2-shared-dev.env`

Observed target:

- `BASE_URL=http://142.171.239.56:7910`
- `TENANT_ID=tenant-1`
- `ORG_ID=org-1`

## Result

The run completed the full chain:

1. `precheck`
2. readonly rerun
3. readonly compare/eval
4. top-level drift audit rendering
5. artifact archive generation

The readonly rerun still returned non-zero because the current `142` state drifted from the frozen readonly baseline, but the wrapper now correctly continued and produced top-level drift audit outputs.

Observed terminal summary:

- `READONLY_EXIT_STATUS=1`
- `DRIFT_VERDICT=FAIL`

This is the intended runtime behavior for investigation:

- preserve failing drift semantics
- still emit the focused audit artifacts required before any refreeze decision

## Output Paths

Run root:

- `tmp/p2-shared-dev-142-drift-audit-20260420-214723/`

Primary artifacts:

- `tmp/p2-shared-dev-142-drift-audit-20260420-214723/current-precheck/OBSERVATION_PRECHECK.md`
- `tmp/p2-shared-dev-142-drift-audit-20260420-214723/current-precheck/summary_probe.json`
- `tmp/p2-shared-dev-142-drift-audit-20260420-214723/current/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-drift-audit-20260420-214723/current/OBSERVATION_DIFF.md`
- `tmp/p2-shared-dev-142-drift-audit-20260420-214723/current/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-142-drift-audit-20260420-214723/DRIFT_AUDIT.md`
- `tmp/p2-shared-dev-142-drift-audit-20260420-214723/drift_audit.json`
- `tmp/p2-shared-dev-142-drift-audit-20260420-214723.tar.gz`

## Drift Summary

Baseline label:

- `shared-dev-142-readonly-20260419`

Current label:

- `current-drift-audit`

Observed metric drift:

- `pending_count: 2 -> 1`
- `overdue_count: 3 -> 4`
- `escalated_count: 1 -> 1`
- `total_anomalies: 2 -> 3`
- `overdue_not_escalated: 1 -> 2`

Approval ID diff:

- added: none
- removed: none

Interpretation:

- this is not an item-set churn problem
- it is a state drift problem inside the same approval population

## Verification Notes

### Precheck

- `AUTH_MODE=password-login`
- `login_http_status=200`
- `summary_http_status=200`

### Readonly compare/eval

The generated readonly evaluation still fails, which is expected:

- `pending_count` drift
- `overdue_count` drift
- `total_anomalies` drift
- `overdue_not_escalated` drift

### Top-level drift audit

Verified present after the readonly failure:

- `DRIFT_AUDIT.md`
- `drift_audit.json`

This closes the runtime gap discovered during the first live execution attempt.

## Conclusion

The shared-dev 142 observation toolchain can now be considered operationally closed:

- merged readonly guard workflow
- merged drift-audit helper
- runtime remediation applied
- real `142` drift-audit executed end-to-end

What remains is an operational decision, not a tooling gap:

- investigate the unexpected drift on `142`
- or run the existing readonly refreeze flow if the drift is accepted
