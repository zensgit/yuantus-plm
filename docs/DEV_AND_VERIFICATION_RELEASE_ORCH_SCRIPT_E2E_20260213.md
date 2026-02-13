# Dev & Verification Report - Release Orchestration Helper Script + E2E Verification (2026-02-13)

This delivery hardens the `scripts/release_orchestration.sh` helper and adds an evidence-grade, self-contained E2E verification that exercises:

- script login flow (no pre-provided JWT)
- plan/execute calls
- baseline release block when e-sign manifest is incomplete
- rollback behavior (`rollback_on_failure=true`)
- e-sign completion via `/api/v1/esign/sign`, followed by a successful execute

## Changes

### 1) Fix helper script correctness bugs

- `scripts/release_orchestration.sh`
  - Build auth headers **after** `ensure_token` so the JWT from login is actually used.
  - Fix JSON payload generation for `execute`: boolean flags are now parsed safely in Python (previously injected `true/false` caused `NameError`).

### 2) Add self-contained E2E verification

- New: `scripts/verify_release_orchestration.sh`
  - Starts a temporary local API server (random port) with a fresh SQLite DB.
  - Creates minimal entities: Item/EBOM + Baseline + WorkCenter + MBOM + Routing (+ operation).
  - Creates an **incomplete** e-sign manifest requiring `meaning=approved`.
  - Runs orchestration via `scripts/release_orchestration.sh`:
    - `plan`: asserts `requires_esign` is present.
    - `execute` with `--include-baselines --rollback-on-failure`: asserts baseline is blocked and routing/mbom are rolled back.
  - Completes the manifest by signing `meaning=approved`, then executes again and asserts final states are `released`.

### 3) Wire into the regression suite (optional)

- `scripts/verify_all.sh`
  - Add `RUN_RELEASE_ORCH=1` optional suite: `Release Orchestration (E2E)`.

### 4) Docs

- `docs/VERIFICATION.md`
  - Document `RUN_RELEASE_ORCH=1` and direct `verify_release_orchestration.sh` usage.
- `docs/RUNBOOK_RELEASE_ORCHESTRATION.md`
  - Clarify that the helper script can auto-login with `--username/--password` when `--token` is not provided.
- `docs/VERIFICATION_RESULTS.md`
  - Record the actual verification run and evidence paths.

## Verification (Executed)

E2E (self-contained):

```bash
bash scripts/verify_release_orchestration.sh
```

Evidence (from the run captured in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_release_orchestration_20260213-195400.log`
- Payloads: `tmp/verify-release-orchestration/20260213-195255/`

