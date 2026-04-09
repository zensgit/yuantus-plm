# DESIGN_PARALLEL_P2_STRICT_GATE_PLAYWRIGHT_RUNNER_RUNTIME_NOTES_20260305

- Date: 2026-03-05
- Scope: strict-gate Playwright execution hardening and runtime-note observability.
- Related code:
  - `scripts/run_playwright_strict_gate.sh`
  - `scripts/strict_gate.sh`
  - `scripts/strict_gate_report.sh`
  - `playwright.config.js`

## 1. Goals

1. Isolate Playwright DB file and port across retries/runs to reduce flaky startup collisions.
2. Add bounded retry logic for retryable bind/startup failures.
3. Keep strict-gate entry scripts (`strict_gate.sh`, `strict_gate_report.sh`) configurable and safe via input validation.
4. Emit runtime-effective Playwright settings into strict-gate markdown report for troubleshooting.

## 2. Non-Goals

1. No change to business APIs in `meta_engine`.
2. No introduction of distributed retry scheduler; retries are local to shell runner.
3. No change to strict-gate pass/fail policy semantics.

## 3. Design Overview

## 3.1 New runner

Add `scripts/run_playwright_strict_gate.sh` as a single execution adapter for Playwright with:

1. Auto port allocation when `PLAYWRIGHT_PORT` is not set.
2. Per-attempt DB path default: `/tmp/yuantus_playwright_${port}_$$.db`.
3. Retry loop controlled by `PLAYWRIGHT_MAX_ATTEMPTS` (default `2`).
4. Retry decision by regex `PLAYWRIGHT_RETRYABLE_PATTERN` (default includes bind/address conflicts).
5. Optional DB cleanup toggle: `PLAYWRIGHT_KEEP_DB=1` keeps sqlite artifacts.
6. Structured stdout keys for downstream parsing:
   - `PLAYWRIGHT_ATTEMPT`
   - `PLAYWRIGHT_PORT`
   - `PLAYWRIGHT_BASE_URL`
   - `PLAYWRIGHT_DB_PATH`
   - `PLAYWRIGHT_MAX_ATTEMPTS`
   - `PLAYWRIGHT_KEEP_DB`
   - `PLAYWRIGHT_RETRYABLE_PATTERN`

## 3.2 strict_gate.sh integration

1. Add `--help` and strict argument validation.
2. Validate `PLAYWRIGHT_MAX_ATTEMPTS` as positive integer.
3. Validate `PLAYWRIGHT_RETRYABLE_PATTERN` as valid ERE before any test execution.
4. Route Playwright step through `PLAYWRIGHT_RUNNER` (default new runner) and pass through runtime env knobs.

## 3.3 strict_gate_report.sh integration

1. Same input validation and runner integration as `strict_gate.sh`.
2. Run id default changed to `STRICT_GATE_<timestamp>_<pid>` to avoid same-second filename collisions.
3. Report default path changed to `docs/DAILY_REPORTS/<run_id>.md` for deterministic run-id to report mapping.
4. Parse runner stdout and backfill effective runtime fields into report Notes section.
5. Derive `PLAYWRIGHT_RETRIED=true|false` from attempt-count.

## 3.4 Playwright config alignment

`playwright.config.js` now derives runtime from env:

1. `PORT` from `PORT` or `YUANTUS_PLAYWRIGHT_PORT`.
2. `YUANTUS_PLAYWRIGHT_DB_PATH` passed into both app DB urls.
3. Startup command uses runtime port and DB path.

## 4. Data/Interface Contract Changes

1. New script contract: `scripts/run_playwright_strict_gate.sh --help` and env-driven execution.
2. `strict_gate.sh` and `strict_gate_report.sh` now expose and validate:
   - `PLAYWRIGHT_RUNNER`
   - `PLAYWRIGHT_MAX_ATTEMPTS`
   - `PLAYWRIGHT_RETRYABLE_PATTERN`
   - `PLAYWRIGHT_KEEP_DB`
   - `PLAYWRIGHT_PORT`
   - `PLAYWRIGHT_BASE_URL`
   - `PLAYWRIGHT_DB_PATH`
3. Strict gate report Notes section includes requested values and effective values parsed from runner output.

## 5. Risks and Mitigations

1. Risk: Over-broad retry regex can hide real failures.
   - Mitigation: custom regex is validated and fully configurable; attempt cap defaults low.
2. Risk: Additional wrapper layer can obscure raw Playwright command failures.
   - Mitigation: runner streams Playwright output and exits with original non-retryable code.
3. Risk: Temp DB cleanup can remove artifacts needed for local debugging.
   - Mitigation: `PLAYWRIGHT_KEEP_DB=1` opt-in retention.

## 6. Rollback Plan

1. Set `PLAYWRIGHT_RUNNER` to legacy direct command path (or bypass runner invocation in scripts) if needed.
2. Revert the three scripts and `playwright.config.js` in one commit.
3. Keep CI contracts to detect accidental partial rollback.
