# DEV_AND_VERIFICATION_SHARED_DEV_142_DRIFT_INVESTIGATION_REAL_EXECUTION_20260420

## Context

- Date: 2026-04-20
- Post-merge target: `main` at `8ddb2ee05f246cf4d4fd34f753fa65928b3b7b33`
- Merged helper PR: `#296` `feat(ops): add shared-dev 142 drift investigation helper`
- Goal: run the new `shared-dev 142` `drift-investigation` entrypoint against the real remote environment and verify that the helper produces a complete evidence pack even when readonly drift still exists

## Command

Executed from a clean post-merge worktree:

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation
```

## Runtime Result

The real run completed the full chain:

1. env validation
2. baseline restore
3. precheck
4. nested readonly rerun
5. nested drift-audit
6. top-level drift investigation rendering
7. final archive write

The run preserved the expected failure semantics:

- `DRIFT_AUDIT_EXIT_STATUS=1`
- `INVESTIGATION_VERDICT=FAIL`
- `INVESTIGATION_CLASSIFICATION=state-drift`

This is the expected outcome for the current `142` state because the helper is designed to keep rendering evidence even when readonly stability fails.

## Real 142 Findings

The post-merge real execution produced:

- `pending_count: 2 -> 1`
- `overdue_count: 3 -> 4`
- `total_anomalies: 2 -> 3`
- `overdue_not_escalated: 1 -> 2`

The approval population itself did not change:

- `added_approval_ids=[]`
- `removed_approval_ids=[]`

So the final classification is:

- `state-drift`

not:

- `membership-drift`
- `mixed-drift`

## Artifacts

Result dir:

- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/`

Top-level investigation pack:

- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/DRIFT_INVESTIGATION.md`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift_investigation.json`

Nested drift-audit pack:

- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/DRIFT_AUDIT.md`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/drift_audit.json`

Nested readonly outputs:

- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/current/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/current/OBSERVATION_DIFF.md`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/current/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/current/summary.json`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/current/items.json`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/current/anomalies.json`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/current/export.json`
- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904/drift-audit/current/export.csv`

Archive:

- `tmp/p2-shared-dev-142-drift-investigation-20260420-223904.tar.gz`

## Verification

Local documentation/index contracts:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Result:

- `3 passed`

Real runtime observations:

- `SUMMARY_HTTP_STATUS=200`
- top-level `DRIFT_INVESTIGATION.md` exists
- top-level `drift_investigation.json` exists
- nested readonly rerun still exits non-zero when drift exists
- investigation wrapper still completes and archives evidence

## Conclusion

`shared-dev 142 drift-investigation` is now verified in two layers:

1. repo-side helper/contracts (`#296`)
2. post-merge real execution on `142`

The remaining decision is operational, not tooling:

- investigate the state drift root cause
- or deliberately refreeze once that drift is understood and accepted
