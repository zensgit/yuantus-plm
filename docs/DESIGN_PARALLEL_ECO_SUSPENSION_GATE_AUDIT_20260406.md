# Design: ECO Suspension Gate Audit

## Date

2026-04-06

## Scope

Audit current ECO lifecycle surfaces to determine whether the system already has
an effective suspension model, and what minimum work remains for `C2`:

- explicit suspended state semantics
- unsuspend gate semantics
- lifecycle and diagnostics consistency

Audit-only package. No code changes are required for this document.

## Current Capabilities

| Capability | Status | Evidence |
| --- | :---: | --- |
| ECO lifecycle states exist | YES | `draft`, `progress`, `conflict`, `approved`, `done`, `canceled` |
| Activity gate blocks critical transitions | YES | `_ensure_activity_gate_ready()` on move/apply |
| Apply diagnostics surface exists | YES | `GET /eco/{eco_id}/apply-diagnostics` |
| Approval rejection can mark visual blocked state | YES | `reject()` sets `kanban_state = "blocked"` |
| Cancel is available as terminal stop action | YES | `POST /eco/{eco_id}/cancel` |
| Stage move is available | YES | `POST /eco/{eco_id}/move-stage` |
| Explicit suspended lifecycle state | NO | no `suspended` in `ECOState` |
| Explicit suspend / unsuspend endpoints | NO | no router surface |
| Unsuspend gate diagnostics | NO | no contract or diagnostics concept |
| Blocked visual state participates in lifecycle gate | NO | `kanban_state` not checked in transitions |

## Audit Matrix

| Concern | Current implementation | Target parity | Gap? | Gap type | Suggested fix | Likely files |
| --- | --- | --- | :---: | --- | --- | --- |
| Lifecycle status model | `ECOState` has `draft/progress/conflict/approved/done/canceled` | explicit suspended state if product wants pause/resume semantics | YES | medium code | add `suspended` lifecycle state or equivalent explicit contract | `models/eco.py`, `eco_service.py`, `eco_router.py`, tests |
| Suspension action surface | no suspend endpoint; closest action is `cancel` | dedicated suspend action with non-terminal semantics | YES | medium code | add `suspend` action separate from cancel | `eco_router.py`, `eco_service.py`, tests |
| Unsuspend action surface | no unsuspend endpoint | dedicated `unsuspend` action | YES | medium code | add unsuspend route/service method | `eco_router.py`, `eco_service.py`, tests |
| Gate semantics | activity blockers and apply diagnostics exist, but not unsuspend-specific gating | unsuspend should validate blockers / approvals / stage prerequisites | YES | medium code | add unsuspend gate contract and diagnostics reuse/extension | `eco_service.py`, router/tests |
| Visual blocked signal | approval rejection sets `kanban_state = blocked` while state stays `progress` | keep visual blocked signal as UX cue | PARTIAL | docs-only / keep | retain as display-level signal, but do not treat as substitute for suspension | docs only |
| Approval rejection semantics | rejection returns ECO to `progress` with `blocked` kanban | clear distinction between rejected approval and suspended ECO | YES | docs + code | document distinction and avoid overloading rejection as suspension | docs + future implementation |
| Cancel semantics | cancel is terminal and sets `canceled` + `kanban_state=done` | keep cancel terminal; do not overload as pause | NO | — | none | existing |
| Update/edit semantics | `PUT /eco/{eco_id}` allows update in `draft` and `progress` only | suspended ECO would likely need explicit edit policy | YES | medium code | define whether suspended is editable and enforce consistently | `eco_router.py`, service/tests |
| Diagnostics | apply diagnostics only covers apply preconditions | suspension/unsuspend should have dedicated or extended diagnostics | YES | medium code | add unsuspend diagnostics or extend existing validation contract | `eco_service.py`, router/tests |

## What Is Already Complete

### Existing gate surfaces

The ECO line already has real gate infrastructure:

- activity blockers can block stage move and apply
- apply diagnostics expose structured preconditions
- approval roles and approval completion already participate in lifecycle flow

This is not a greenfield gating problem.

### Existing stop/blocked signals

The system also already has two adjacent semantics:

- `cancel` is a terminal stop
- `reject` can mark an ECO visually `blocked`

These provide useful building blocks, but they do not add up to a suspend /
unsuspend lifecycle.

## Real Gap

### GAP-S1: no explicit suspended lifecycle

There is no `suspended` state in `ECOState`, no dedicated suspend route, and no
resume/unsuspend contract.

That means operators cannot distinguish:

- temporarily paused ECO
- rejected-but-still-progress ECO
- terminally canceled ECO

using first-class lifecycle semantics.

### GAP-S2: `kanban_state = blocked` is only a display hint

Approval rejection sets:

- `eco.state = progress`
- `eco.kanban_state = blocked`

but no core lifecycle handler checks `kanban_state` before:

- update
- move-stage
- apply

So current `blocked` is not a true suspension gate.

### GAP-S3: no unsuspend gate contract

Even if a product team treated `blocked` as “paused”, the system has no explicit
contract for:

- who can unsuspend
- what must be clear before unsuspend
- whether blockers/approvals must be revalidated
- what audit trail and diagnostics should be emitted

## Classification

### **CODE-CHANGE CANDIDATE**

This line is not docs-only.

The remaining work is medium-sized but bounded:

1. add explicit suspend / unsuspend semantics
2. wire them into lifecycle and permission checks
3. define the minimum unsuspend gate contract

No large ECO rewrite is required because lifecycle hooks, apply diagnostics, and
approval infrastructure already exist.

## Minimum Write Set

### Package 1: `eco-suspended-state-and-actions`

Scope:

- add explicit suspended lifecycle contract
- add suspend and unsuspend service/router surfaces
- ensure cancel remains terminal and distinct
- define update/edit behavior for suspended ECOs

Likely files:

- `src/yuantus/meta_engine/models/eco.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- ECO lifecycle tests

Estimated size: medium
Risk: medium

### Package 2: `eco-unsuspend-gate-and-diagnostics`

Scope:

- define unsuspend gate checks using existing activity/approval infrastructure
- add dedicated diagnostics or extend current release-style diagnostics
- lock reject vs suspend vs cancel semantics with focused tests

Likely files:

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- ECO diagnostics and lifecycle tests

Estimated size: medium
Risk: medium

## Recommended Order

1. `eco-suspended-state-and-actions`
2. `eco-unsuspend-gate-and-diagnostics`

Reason:

- lifecycle semantics must exist before an unsuspend gate can be meaningful
- otherwise the system keeps overloading `progress + blocked` as a pseudo-state

## Closure Verdict

This line is **not closed yet**.

The ECO module already has blockers, approvals, diagnostics, and terminal cancel
semantics, but it does not yet have a real suspend / unsuspend lifecycle. The
remaining work is a bounded medium-sized suspension contract package, not a
large refactor.
