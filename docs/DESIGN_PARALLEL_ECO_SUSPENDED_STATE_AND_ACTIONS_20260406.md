# Parallel ECO Suspended State And Actions

## Date

2026-04-06

## Goal

Close package 1 from the ECO suspension audit by adding an explicit suspended lifecycle state plus narrow suspend/unsuspend actions.

## Scope

- Add `ECOState.SUSPENDED`
- Add `POST /eco/{eco_id}/suspend`
- Add `POST /eco/{eco_id}/unsuspend`
- Block lifecycle bypass through:
  - `move_to_stage`
  - `new_revision`
  - approval `approve`
  - approval `reject`

## Contract

### Suspend

- Allowed from non-terminal states
- Rejected from `done`, `canceled`, and already `suspended`
- Sets:
  - `state = suspended`
  - `kanban_state = blocked`
  - `approval_deadline = null`
- Optional `reason` is appended into `description` as `[SUSPENDED] ...`
- Runs workflow custom actions on `before` and `after`

### Unsuspend

- Allowed only from `suspended`
- Default `resume_state = progress`
- Explicit `resume_state` allowed:
  - `draft`
  - `progress`
  - `conflict`
  - `approved`
- Sets:
  - `state = resume_state`
  - `kanban_state = normal`
- Re-applies stage SLA when resuming into non-approved states
- Clears approval deadline when resuming into `approved`
- Runs workflow custom actions on `before` and `after`

## Guardrails

- `move_to_stage` now fails while suspended
- `action_new_revision` now fails while suspended
- `approve` now fails while suspended
- `reject` now fails while suspended

## Non-Goals

- No unsuspend diagnostics yet
- No separate suspend audit/export surface
- No workflow DSL changes
- No migration beyond enum/state usage

## Result

This package gives ECO an explicit pause/resume lifecycle without expanding into diagnostics. It is intentionally narrow so package 2 can focus on unsuspend gate/diagnostics rather than basic state transitions.
