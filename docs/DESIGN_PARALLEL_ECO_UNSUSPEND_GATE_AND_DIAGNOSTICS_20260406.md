# Parallel ECO Unsuspend Gate And Diagnostics

## Date

2026-04-06

## Goal

Close package 2 from the ECO suspension audit by turning `unsuspend` into a gated transition instead of a blind state flip.

## Scope

- Add `GET /eco/{eco_id}/unsuspend-diagnostics`
- Add side-effect-free service diagnostics for unsuspend
- Gate `POST /eco/{eco_id}/unsuspend` by default
- Allow `force=true` to bypass the gate when an operator explicitly chooses to do so

## Rules

The diagnostics surface uses a narrow fixed ruleset:

- `eco.exists`
- `eco.state_suspended`
- `resume_state.allowed`
- `eco.activity_blockers_clear`
- `eco.stage_consistency`
- `eco.approval_consistency`

## Behavior

### Diagnostics endpoint

- Returns `200`
- Uses the standard release-diagnostics response shape
- Returns structured `errors` / `warnings`
- Requires unsuspend permission when the ECO exists

### Unsuspend endpoint

- Default path runs diagnostics first
- When diagnostics contain errors, returns `400`
- Error message points operators to `/unsuspend-diagnostics`
- `force=true` bypasses diagnostics but still calls the normal unsuspend action

## Approval consistency

- `resume_state=approved` is allowed only when the current stage approvals are complete
- For non-approved resume states, approval consistency does not block unsuspend

## Non-Goals

- No export surface
- No batch unsuspend
- No general ruleset DSL
- No monitoring board or operator summary surface

## Result

With this package, ECO suspension now has both explicit lifecycle actions and a minimal operator-facing gate for safe unsuspend.
