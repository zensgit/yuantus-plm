# DEV AND VERIFICATION - P2 Remote Observation Validation - 2026-04-18

## Goal

Freeze this round of remote P2 observation execution as a compact verification record, separate from the deployment remediation notes.

## Environment Boundary

- Host: `<remote-host>`
- Remote workspace: `<remote-workspace>`
- Runtime container: `<api-container>`
- Base URL: `http://127.0.0.1:7910`
- Environment identity: temporary remote `local-dev-env`
- Tenant / org: `tenant-1 / org-1`
- Accounts:
  - seeded `admin`
  - seeded `ops-viewer`

This run used `local-dev-env` semantics on a remote host. It proves the observation toolchain can run remotely, but it is not a shared-dev observation baseline.

## Executed Flow

The remote execution flow was:

1. Run `scripts/verify_p2_dev_observation_startup.sh`
2. Run `scripts/render_p2_observation_result.py`
3. Review `OBSERVATION_RESULT.md`
4. Run write-path checks for permission and escalation behavior
5. Re-run verify and render to confirm state transition in the rendered result

## Result A - Startup Verification

`verify_p2_dev_observation_startup.sh` passed. The following read endpoints all returned `200`:

- `GET /api/v1/eco/approvals/dashboard/summary`
- `GET /api/v1/eco/approvals/dashboard/items`
- `GET /api/v1/eco/approvals/dashboard/export?fmt=json`
- `GET /api/v1/eco/approvals/dashboard/export?fmt=csv`
- `GET /api/v1/eco/approvals/audit/anomalies`

## Result B - Baseline Rendered Observation

The first rendered `OBSERVATION_RESULT.md` reported:

- `pending_count = 1`
- `overdue_count = 2`
- `escalated_count = 0`
- `total_anomalies = 2`
- `overdue_not_escalated = 2`
- `escalated_unresolved = 0`
- `no_candidates = 0`

## Result C - Write-Path Checks

### Permission Check

| Scenario | HTTP | Expected |
|---|---:|---|
| `ops-viewer -> POST /api/v1/eco/{eco-specialist}/auto-assign-approvers` | `403` | unauthorized actor is blocked |
| `admin -> POST /api/v1/eco/{eco-specialist}/auto-assign-approvers` | `200` | authorized actor can assign approvers |

### Escalation Check

| Scenario | HTTP | Expected |
|---|---:|---|
| `admin -> POST /api/v1/eco/approvals/escalate-overdue` | `200` | overdue approval is escalated |

Observed write outcome:

- `ops-viewer` was rejected with `Forbidden: insufficient ECO permission`
- `admin` successfully auto-assigned approvers on `eco-specialist`
- `admin` escalated one overdue item

## Result D - Re-Rendered Observation

After write-path execution, the re-rendered `OBSERVATION_RESULT.md` reported:

- `pending_count = 2`
- `overdue_count = 3`
- `escalated_count = 1`
- `total_anomalies = 2`
- `escalated_unresolved = 1`
- `overdue_not_escalated = 1`
- `no_candidates = 0`

## Interpretation

- The remote environment successfully completed the full observation loop: startup verify, render, write check, and re-render.
- One item moved from `overdue_not_escalated` to `escalated_unresolved`, which confirms the escalation transition is visible in the rendered artifact.
- `no_candidates = 0` remained stable, which matches the current seeded local-dev expectation.
- The result is sufficient as a remote execution proof for P2 observation tooling, but it should not be presented as shared-dev operational evidence.

## Result E - Frozen Remote Observation Round 1

After the initial remote validation, the environment was intentionally kept in place and re-observed without rebuild or reseed.

The frozen round-1 baseline was rendered from:

- `<remote-workspace>/remote-dev-results/round1-before`

The rendered `OBSERVATION_RESULT.md` reported:

- `pending_count = 2`
- `overdue_count = 3`
- `escalated_count = 1`
- `total_anomalies = 2`
- `escalated_unresolved = 1`
- `overdue_not_escalated = 1`
- `no_candidates = 0`

Interpretation:

- This is the stable remote baseline for the current frozen environment.
- It is not identical to the clean local seed baseline because the remote environment already contains one prior successful auto-assign and one prior escalation.
- The anomaly shape is still consistent with the known post-write state from the earlier remote validation round.

## Result F - Minimal State-Change Re-Check

One additional `POST /api/v1/eco/approvals/escalate-overdue` call was executed against the frozen environment.

Observed result:

- HTTP `200`
- response body: `{"escalated":0,"items":[]}`

The re-rendered result from:

- `<remote-workspace>/remote-dev-results/round1-after`

remained unchanged:

- `pending_count = 2`
- `overdue_count = 3`
- `escalated_count = 1`
- `escalated_unresolved = 1`
- `overdue_not_escalated = 1`

Reason:

- The only remaining `overdue_not_escalated` sample is `eco-overdue-admin`
- Its pending overdue approval is already assigned to `admin`
- This matches the known idempotent guard path, so a second escalation pass does not create another escalated approval

This means the frozen remote environment is stable, but it is no longer suitable for demonstrating another positive escalation transition without a deliberate reseed or rebuild.

## Freeze Decision

- Keep the current `<remote-host>:<remote-workspace>` deployment as the temporary remote `local-dev-env` observation surface
- Do not rebuild or reseed it unless the goal is to intentionally reset the baseline
- Use the current frozen state as the remote regression observation surface before future P2 approval-chain changes

## Artifacts

- Initial remote validation result: `<remote-workspace>/local-dev-env/results/OBSERVATION_RESULT.md`
- Frozen round-1 baseline result: `<remote-workspace>/remote-dev-results/round1-before/OBSERVATION_RESULT.md`
- Frozen round-1 re-check result: `<remote-workspace>/remote-dev-results/round1-after/OBSERVATION_RESULT.md`
- Operator runbook: `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`
- Related remediation notes: `docs/DEV_AND_VERIFICATION_REMOTE_DEPLOY_REMEDIATION_20260418.md`

## Verification

The documentation change should keep the delivery doc index complete for this new report entry.
