# DEV AND VERIFICATION - P2 Local Dev Env Experiments - 2026-04-18

## Goal

Freeze the two most valuable `local-dev-env` manual experiments as the baseline self-check set for future P2 approval-chain changes.

## Environment Boundary

- Environment: `local-dev-env`
- Base URL: `http://127.0.0.1:7910`
- Tenant / org: `tenant-1 / org-1`
- Users:
  - `admin / admin`
  - `ops-viewer / ops123`

This is a local-only sandbox. It is not shared dev and does not replace shared-dev observation.

## Experiment A - Escalation State Transition

### Before

- `pending_count = 1`
- `overdue_count = 2`
- `escalated_count = 0`
- `overdue_not_escalated = 2`
- `escalated_unresolved = 0`

### After

- `pending_count = 1`
- `overdue_count = 3`
- `escalated_count = 1`
- `overdue_not_escalated = 1`
- `escalated_unresolved = 1`

### Interpretation

- One ECO moved from `overdue_not_escalated` to `escalated_unresolved`
- `eco-overdue-admin` stayed untouched because the pending admin approval triggered the idempotent guard
- `eco-overdue-opsview` escalated successfully to `admin`
- `overdue_count` increased because the newly created pending admin approval is itself overdue and the dashboard counts `ECOApproval` rows

## Experiment B - Permission Tri-State

| Scenario | Actor | HTTP | Expected outcome |
|---|---|---:|---|
| No token | — | 401 | `Unauthorized` |
| Non-superuser, no permission | `ops-viewer` | 403 | `Forbidden: insufficient ECO permission` |
| Superuser | `admin` | 200 | approval created / assigned normally |

### Interpretation

- Router-level authentication and service-level permission checks are both active
- Auto-assign does not silently succeed for unauthorized actors
- The local environment is sufficient to validate `401 / 403 / 200` semantics

## Baseline Decision

The following two experiments are now the fixed local baseline set:

1. Escalation state transition
2. Permission tri-state

Do not keep expanding local experiments unless a future runtime change specifically breaks one of these semantics.

## Recommended Reuse

After any code change touching:

- ECO approval routing
- auto-assign
- escalation
- dashboard
- audit

rerun:

1. `./local-dev-env/start.sh`
2. one full observation smoke
3. Experiment A
4. Experiment B

## Verification

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Result:

- `5 passed`
