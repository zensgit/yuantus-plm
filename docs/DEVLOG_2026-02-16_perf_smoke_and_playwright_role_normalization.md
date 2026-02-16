# DEVLOG 2026-02-16: Perf Smoke Harness + verify_all Wiring + Playwright Role-Normalization Coverage

## Scope

Implemented the full `1 + 2 + 3` package:

1. Add self-contained perf smoke scripts for `release-orchestration`, `reports`, and `e-sign` with p95 threshold assertions.
2. Wire these perf smokes into `scripts/verify_all.sh` behind explicit optional toggles.
3. Add Playwright API-only regression coverage for superuser and mixed-case role behavior (including report export endpoint).

## Deliverables

### 1) New self-contained perf smoke scripts

Added:

- `scripts/verify_release_orchestration_perf_smoke.sh`
- `scripts/verify_reports_perf_smoke.sh`
- `scripts/verify_esign_perf_smoke.sh`

Common behavior:

- Starts isolated local API server (`uvicorn`) on an ephemeral port.
- Uses isolated SQLite DB under `/tmp`.
- Seeds identity/meta via CLI.
- Captures endpoint latency samples.
- Computes p95 and asserts threshold.
- Writes metrics artifacts to `tmp/.../metrics_*.json`.

Threshold env knobs:

- Release orchestration:
  - `PERF_RELEASE_ORCH_SAMPLES`
  - `PERF_RELEASE_ORCH_PLAN_MAX_MS`
  - `PERF_RELEASE_ORCH_EXECUTE_DRY_RUN_MAX_MS`
- Reports:
  - `PERF_REPORTS_SAMPLES`
  - `PERF_REPORTS_PART_COUNT`
  - `PERF_REPORTS_SEARCH_MAX_MS`
  - `PERF_REPORTS_SUMMARY_MAX_MS`
  - `PERF_REPORTS_EXPORT_MAX_MS`
- E-sign:
  - `PERF_ESIGN_SAMPLES`
  - `PERF_ESIGN_SIGN_MAX_MS`
  - `PERF_ESIGN_VERIFY_MAX_MS`
  - `PERF_ESIGN_AUDIT_SUMMARY_MAX_MS`

### 2) `verify_all` integration (optional toggles)

Updated `scripts/verify_all.sh`:

- Added toggles:
  - `RUN_RELEASE_ORCH_PERF`
  - `RUN_REPORTS_PERF`
  - `RUN_ESIGN_PERF`
- Added startup summary printing for the three toggles.
- Added optional run blocks:
  - `Release Orchestration (Perf Smoke)`
  - `Reports (Perf Smoke)`
  - `E-Sign (Perf Smoke)`

Usage example:

```bash
RUN_RELEASE_ORCH_PERF=1 RUN_REPORTS_PERF=1 RUN_ESIGN_PERF=1 \
  bash scripts/verify_all.sh
```

### 3) Playwright API-only regression for role normalization

Added:

- `playwright/tests/admin_role_normalization.spec.js`

Coverage:

- Superuser user (with non-admin org role) can access:
  - `GET /api/v1/release-orchestration/items/{item_id}/plan`
  - `GET /api/v1/esign/audit-summary`
- Mixed-case/whitespace role matching for reports export:
  - create normal user with role `" Viewer "`
  - create public report definition with `allowed_roles: [" viewer "]`
  - verify `POST /api/v1/reports/definitions/{id}/export` succeeds and returns CSV attachment.

## CI Contract Extensions

Added:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py`

Checks:

- New `RUN_*_PERF` toggle definitions and summary lines exist in `verify_all.sh`.
- New perf scripts are wired as optional `run_test` blocks with correct `skip_test` reasons.

Updated:

- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

Added syntax-validation coverage for:

- `verify_release_orchestration_perf_smoke.sh`
- `verify_reports_perf_smoke.sh`
- `verify_esign_perf_smoke.sh`

## Validation Executed

### A) Contract + syntax tests

```bash
./.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
```

Result:

- `5 passed`

### B) Perf smoke scripts (real run)

```bash
PERF_RELEASE_ORCH_SAMPLES=3 bash scripts/verify_release_orchestration_perf_smoke.sh
PERF_REPORTS_SAMPLES=3 PERF_REPORTS_PART_COUNT=12 bash scripts/verify_reports_perf_smoke.sh
PERF_ESIGN_SAMPLES=3 bash scripts/verify_esign_perf_smoke.sh
```

Result:

- all three scripts: `ALL CHECKS PASSED`

### C) Playwright new spec

`playwright.config.js` has `reuseExistingServer: true`, so local runs can accidentally reuse an unrelated pre-running `:7910` service.
For deterministic validation, this delivery was verified with an isolated temporary Playwright config and dedicated port.

```bash
npx playwright test --config=/tmp/pw-role-norm.config.js \
  playwright/tests/admin_role_normalization.spec.js
```

Result:

- `1 passed`

