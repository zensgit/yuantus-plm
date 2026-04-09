# Design: Workflow Custom Action Context Predicates and Tests

## Date

2026-04-06

## Goal

Implement the second closure package for workflow custom action predicates:

- add white-listed context predicates for `actor_roles`, `product_id`, and
  `eco_type`
- inject those context values in the existing manual-execute and ECO-hook paths
- lock the contract with focused tests

This package intentionally avoids a generic predicate DSL.

## Changes

### 1. `match_predicates` whitelist expanded

The allowed predicate set now includes:

- `stage_id`
- `eco_priority`
- `actor_roles`
- `product_id`
- `eco_type`

Validation rules:

- unsupported keys are rejected
- `eco_priority` still validates against `low|normal|high|urgent`
- `eco_type` validates against `bom|product|document`
- `actor_roles` must be an array of strings

### 2. Runtime context now carries business-scoped fields

`WorkflowCustomActionService` now normalizes runtime context for:

- `actor_roles`
- `product_id`
- `eco_type`

Matching behavior:

- `actor_roles` uses intersection semantics
- `product_id` uses exact match
- `eco_type` uses exact match

### 3. Manual execute path injects actor roles

`POST /workflow-actions/execute` now merges the current user's roles into
`context["actor_roles"]` when the caller does not provide it explicitly.

This keeps the existing request shape while making role-scoped rules testable
through the router surface.

### 4. ECO hooks now provide product/type/actor context

`ECOService._run_custom_actions()` already exposed stage/priority scope from the
previous package. This package adds:

- `eco_type`
- `product_id`
- actor roles resolved from `user_id -> RBACUser.roles`

That makes ECO lifecycle hooks usable for:

- product-specific rules
- ECO-type-specific rules
- actor-role-scoped rules

## Why this closes the second package

The audit recommended that the next step after runtime scope should be a small,
white-listed business-context layer rather than a generic rule language.

This package does exactly that:

- it adds the highest-value context predicates
- it keeps matching explicit and allowlisted
- it avoids expression parsing, dynamic field lookup, or custom scripting

## Non-Goals

- arbitrary field/value predicates
- custom predicate DSL
- product hierarchy predicates
- free-form actor identity matching

## Files

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`

## Result

Workflow custom action predicates now cover:

- runtime scope: `workflow_map_id`, `stage_id`, `eco_priority`
- business context: `actor_roles`, `product_id`, `eco_type`

with focused contract coverage and without turning the feature into a generic
rules engine.
