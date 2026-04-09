# Design: Workflow Custom Action Runtime Scope Predicates

## Date

2026-04-05

## Goal

Implement the first closure package from the workflow custom action predicate
audit:

- honor `workflow_map_id` during runtime matching
- add first-class runtime predicates for `stage_id` and ECO `priority`
- widen ECO hook context just enough to evaluate those predicates

This package intentionally does **not** add actor / role / arbitrary field
predicates.

## Changes

### 1. Rule contract adds `match_predicates`

`POST /workflow-actions/rules` now accepts an optional top-level
`match_predicates` object.

Supported keys in this package:

- `stage_id`
- `eco_priority`

Validation rules:

- unsupported predicate keys are rejected
- `eco_priority` must be one of `low | normal | high | urgent`

The normalized predicates are stored inside `action_params["match_predicates"]`
so no schema migration is required.

### 2. Runtime matching now honors scope predicates

`WorkflowCustomActionService.evaluate_transition()` still matches by:

- `target_object`
- `trigger_phase`
- `from_state`
- `to_state`

and now also filters by:

- rule `workflow_map_id` when present
- `match_predicates.stage_id`
- `match_predicates.eco_priority`

Rules without these scope predicates continue to behave as global rules within
the existing transition scope.

### 3. ECO hook context is widened

`ECOService._run_custom_actions()` now passes runtime context with:

- `source`
- `eco_id`
- `stage_id`
- `eco_priority`
- `workflow_map_id` when available

`move_to_stage()` explicitly overrides `stage_id` for the `before` hook so
stage-scoped rules can match the destination stage instead of the pre-move
stage.

## Why this closes the first package

The audit identified two immediate correctness gaps:

1. `workflow_map_id` existed in rule configuration but was inert at runtime
2. runtime matching had no first-class stage / priority scope

This package closes both gaps without introducing a generic expression system.

## Non-Goals

- actor / role predicates
- arbitrary field/value predicates
- product-scope predicates
- conflict-scope redesign

Those remain candidates for a later package if still needed.

## Files

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`

## Result

Workflow custom action matching is no longer transition-only. Runtime scope now
supports:

- workflow map scoping
- stage scoping
- ECO priority scoping

with focused contract coverage and no migration.
