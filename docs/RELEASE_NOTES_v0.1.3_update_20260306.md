# Release Notes v0.1.3 (Update 2026-03-06)

## Highlights

- Extended Parallel P2 breakage/helpdesk capabilities:
  - failure replay trends query + export (`json/csv/md`)
  - replay cleanup dry-run + archive behavior
  - replay thresholds/hints/alerts/metrics integration
- Added router/service/e2e/contracts test coverage for replay and doc-sync gate paths.
- Added Parallel P2 delivery closure and final handoff documents.
- Hardening update:
  - migrated FastAPI app lifecycle to `lifespan` (replace deprecated `on_event` hooks)
  - migrated AML schema config to Pydantic v2 `ConfigDict`
  - replaced mutable model defaults with `default_factory`

## Commits

- `7fdd4cd` feat(parallel-p2): extend replay trends cleanup alerts and doc-sync gate
- `6cfd3c9` test(parallel-p2): add replay/doc-sync gate coverage and contracts
- `f36c8ec` docs(parallel-p2): add design and verification handoff set

## Verification

- Gate regression: `bash scripts/strict_gate.sh` -> PASS
- Strict gate report: `scripts/strict_gate_report.sh` -> PASS
- Extended strict gate report:
  - `RUN_RUN_H_E2E=1 RUN_IDENTITY_ONLY_MIGRATIONS_E2E=1 scripts/strict_gate_report.sh` -> PASS
  - Report: `docs/DAILY_REPORTS/STRICT_GATE_20260306-134203_34575.md`
- Optional delivery checks:
  - `bash scripts/verify_release_orchestration.sh` -> PASS
  - `bash scripts/verify_release_orchestration_perf_smoke.sh` -> PASS
  - `bash scripts/verify_esign_perf_smoke.sh` -> PASS
  - `bash scripts/verify_reports_perf_smoke.sh` -> PASS

## Notes

- Remaining items are non-blocking hardening follow-ups only.
