# Parallel P2 Delivery Closure Design (2026-03-06)

## 1. Goal

Close Parallel P2 delivery with a release-ready baseline by converging three tracks:

1. Functional closure: breakage/helpdesk replay + trends + cleanup + alerts are complete and test-covered.
2. Verification closure: strict gate + optional release/e2e/perf evidence are all green.
3. Release closure: no blocking gaps remain before branch split and handoff.

## 2. Scope Freeze

In-scope closure objects:

- Breakage helpdesk replay trends APIs and exports.
- Replay cleanup dry-run and archive behavior.
- Replay alert thresholds and metrics integration.
- Doc-sync gate and version checkout contracts introduced in P2.
- Delivery documentation and verification evidence indexing.

Out-of-scope for this closure slice:

- Framework-level warning cleanup (FastAPI `on_event`, Pydantic class-based config migration).
- Broader platform perf baselines outside release/e-sign/reports smoke.

## 3. Release Gate Criteria

Release gate is considered pass only when all items hold:

1. Contract and regression tests for touched P2 modules pass.
2. `strict_gate.sh` and `strict_gate_report.sh` pass.
3. Optional but recommended evidence checks pass:
   - `verify_run_h_e2e.sh`
   - `verify_identity_only_migrations.sh`
   - `verify_release_orchestration.sh`
   - `verify_release_orchestration_perf_smoke.sh`
   - `verify_esign_perf_smoke.sh`
   - `verify_reports_perf_smoke.sh`
4. Delivery docs are indexed and sorting/completeness contracts remain green.

## 4. Commit Split Plan

Recommended split for final integration:

1. `feat(parallel-p2): replay trends/export/cleanup dry-run + replay alerts/metrics`
2. `test(parallel-p2): router/service/e2e/contracts coverage expansion`
3. `docs(parallel-p2): design + dev/verification evidence + delivery index sync`

Rationale:

- Keep behavior changes isolated from tests and docs.
- Reduce revert blast radius.
- Improve reviewability for final handoff.

## 5. Risk and Mitigation

1. Risk: large patch size across service/router/tests.
   - Mitigation: split commits by behavior/testing/docs and preserve strict gate evidence.
2. Risk: downstream scripts relying on CSV columns may be sensitive to replay export field extension.
   - Mitigation: preserve backward fields and document newly added columns.
3. Risk: warning noise hides regressions.
   - Mitigation: warnings treated as non-blocking, but tracked for post-delivery hardening.

## 6. Done Definition

This closure is done when:

- All release gate checks above pass.
- Evidence markdown and output logs are available and linked.
- Remaining work is only non-blocking hardening tasks.
