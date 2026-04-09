# Design: Workflow Custom Action Predicate Upgrade Audit

## Date

2026-04-05

## Scope

Audit current workflow custom action surfaces to determine the remaining work
for `C1`:

- richer runtime predicates for workflow custom actions
- clearer scope matching for ECO transition hooks
- minimum write set needed before this line can be closed

Audit-only package. No code changes are required for this document.

## Current Capabilities

| Capability | Status | Evidence |
| --- | :---: | --- |
| Rule CRUD-lite surface exists | YES | `POST /workflow-actions/rules`, `GET /workflow-actions/rules` |
| Manual execution preview surface exists | YES | `POST /workflow-actions/execute` |
| Target object scoping exists | YES | `target_object` on rule + runtime filter |
| Transition phase scoping exists | YES | `trigger_phase=before|after` |
| State transition scoping exists | YES | `from_state`, `to_state` |
| Deterministic ordering exists | YES | priority sort in `evaluate_transition()` |
| Fail strategies exist | YES | `block`, `warn`, `retry` |
| Retry / timeout normalization exists | YES | `_normalize_retry_max()`, `_normalize_timeout_s()` |
| ECO hooks are wired | YES | `move_to_stage()` and `action_apply()` call `_run_custom_actions()` |
| Runtime workflow map scoping | NO | `workflow_map_id` stored, not matched in `evaluate_transition()` |
| Rich runtime predicates | NO | no stage / role / field / priority / product matching |
| Context-aware filtering | PARTIAL | context is passed to actions, not used for rule selection |

## Audit Matrix

| Concern | Current implementation | Target parity | Gap? | Gap type | Suggested fix | Likely files |
| --- | --- | --- | :---: | --- | --- | --- |
| Phase + state gating | runtime matches `target_object`, `trigger_phase`, `from_state`, `to_state` | keep current transition-level gating | NO | — | none | `parallel_tasks_service.py` |
| Ordering | matched rules sorted by normalized priority, then name/id | stable execution order | NO | — | none | `parallel_tasks_service.py` |
| Failure behavior | `block`, `warn`, `retry` already enforced with result codes | keep current fail contract | NO | — | none | `parallel_tasks_service.py` |
| ECO hook coverage | ECO stage move/apply already run before/after hooks | stable ECO lifecycle hook coverage | NO | — | none | `eco_service.py` |
| Workflow map scope | `workflow_map_id` is stored and included in conflict counting, but ignored during runtime selection | runtime should honor workflow-map scope when present | YES | medium code | include `workflow_map_id` in runtime matching and pass effective workflow scope in context | `parallel_tasks_service.py`, `parallel_tasks_router.py`, `eco_service.py` |
| Stage / ECO priority predicates | no runtime predicate model beyond states; `stage_id` and `priority` are not match inputs | rules should optionally narrow on stage / ECO priority | YES | medium code | add normalized predicate schema and match against runtime context | `parallel_tasks_service.py`, `parallel_tasks_router.py`, `eco_service.py` |
| Actor / role predicates | no user / role data participates in rule matching | rules should optionally narrow on actor / role when needed | YES | medium code | extend execution context and predicate matcher for user / role filters | `parallel_tasks_service.py`, `parallel_tasks_router.py`, `eco_service.py` |
| Field / value predicates | no generic field comparison exists | rules should optionally match on selected context fields | YES | medium code | add explicit allowlisted field predicates rather than free-form eval | `parallel_tasks_service.py`, router/tests |
| Product scope predicates | no product / item scoping in runtime matcher | rules should optionally narrow on product scope | YES | medium code | pass `product_id` / related ids into ECO context and match via normalized predicates | `eco_service.py`, `parallel_tasks_service.py` |
| Router/test contract clarity | router request model has no dedicated predicate shape; tests only cover invalid payload + execution failure | focused contract tests for predicate payload and runtime matching | YES | small-medium code | add predicate-focused router/service tests after implementation | router/service tests |

## What Is Already Complete

### Execution engine

The execution engine itself is already solid:

- deterministic ordering via priority
- bounded retry / timeout behavior
- explicit fail-strategy result codes
- execution records in `WorkflowCustomActionRun`

This is not an execution-engine refactor.

### ECO hook integration

The ECO lifecycle is already wired into custom actions:

- `move_to_stage()` runs `before` and `after`
- `action_apply()` runs `before` and `after`
- context already carries `source`, `eco_id`, and `stage_id`

This means the missing work is predicate selection, not hook installation.

## Real Gaps

### GAP-W1: runtime matching is still transition-only

Today a rule matches if:

- `target_object` matches
- `trigger_phase` matches
- `from_state` matches when present
- `to_state` matches when present

There is no second-stage predicate filter for:

- `workflow_map_id`
- `stage_id`
- ECO `priority`
- actor / role
- product scope
- allowlisted field/value comparisons

This is the main reason the line is not closed.

### GAP-W2: `workflow_map_id` is configuration-only

`workflow_map_id` exists on the rule model and participates in
`conflict_scope`, but runtime evaluation never checks it. That makes the field
discoverable in API payloads while still being operationally inert.

This is a real code gap, not a docs gap.

### GAP-W3: execution context is too thin for richer predicates

`_run_custom_actions()` currently passes:

- `source`
- `eco_id`
- `stage_id`

That is enough for diagnostics, but not enough for richer predicate matching.
If the product wants stage / role / product / priority-aware actions, the
context contract needs to be widened in a controlled way.

## Classification

### **CODE-CHANGE CANDIDATE**

This line is not docs-only yet.

The remaining work is medium-sized but bounded:

1. add normalized runtime predicate matching
2. widen ECO execution context just enough for those predicates
3. add focused contract tests for predicate payloads and matching

No large refactor is required because hooks, ordering, and fail handling are
already present.

## Minimum Write Set

### Package 1: `workflow-custom-action-runtime-scope-predicates`

Scope:

- add a normalized optional predicate block for rules
- honor `workflow_map_id` during runtime matching
- support first-class runtime predicates for `stage_id` and ECO `priority`
- widen ECO hook context with the minimum needed match fields

Likely files:

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- workflow custom action service/router tests

Estimated size: medium
Risk: medium

### Package 2: `workflow-custom-action-context-predicates-and-tests`

Scope:

- add actor / role / allowlisted field-value predicates
- add focused router and service tests for predicate payload validation
- lock matching behavior for missing / partial context

Likely files:

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- workflow custom action tests

Estimated size: medium
Risk: medium

## Recommended Order

1. `workflow-custom-action-runtime-scope-predicates`
2. `workflow-custom-action-context-predicates-and-tests`

Reason:

- `workflow_map_id` being inert is the clearest correctness gap
- stage / priority predicates fit naturally into the existing ECO hook context
- actor / field predicates should be added only after the runtime predicate
  model is stable

## Closure Verdict

This line is **not closed yet**.

Workflow custom actions already have stable hooks, ordering, and fail
semantics, but their runtime selection model is still transition-only. The
remaining work is a bounded medium-sized predicate upgrade, not a large
workflow-engine rewrite.
