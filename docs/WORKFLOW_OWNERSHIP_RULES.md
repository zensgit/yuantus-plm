# Workflow Ownership Rules

## Purpose

Prevent Yuantus and Metasheet from building overlapping workflow engines for the same business responsibility.

The deciding question is:

`Does this workflow own or mutate PLM object state?`

If yes, Yuantus owns it.

## Hard Rule

### Yuantus Owns PLM Object Workflows

Any workflow that changes, approves, gates, or releases a PLM object must be executed by Yuantus-owned workflow or approval APIs.

This includes:

- item lifecycle transitions
- BOM governance transitions
- ECO approval and rejection
- release readiness and release execution
- version/revision gates
- approvals that write back to PLM object state

### Metasheet Owns Non-PLM Workflows

Any workflow that coordinates people or tasks without owning PLM object state belongs to Metasheet.

This includes:

- onboarding
- reimbursement
- internal department requests
- general project coordination
- non-PLM office workflows

## Gray-Zone Rule

If the workflow has external collaboration or portal UX but the final decision changes PLM object state:

- Yuantus owns the state machine and approval decision
- Metasheet may own the UI, portal, inbox, or orchestration layer
- the final mutation must still call Yuantus APIs

Typical example:

- supplier drawing review

The supplier-facing UI may live in Metasheet, but approval state that affects ECO, item, or release status still belongs to Yuantus.

## Ownership Matrix

| Scenario | Owner | Why |
| --- | --- | --- |
| ECO multi-step approval | Yuantus | ECO state and release consequences are PLM authority |
| Item release gate | Yuantus | Release semantics and object integrity live in PLM |
| BOM review and acceptance | Yuantus | BOM structure and downstream release impact live in PLM |
| New employee onboarding | Metasheet | No PLM object authority involved |
| Expense reimbursement | Metasheet | Administrative workflow, not PLM state |
| Supplier portal collecting feedback for a PLM object | Metasheet UI + Yuantus authority | Collaboration outside, state ownership inside PLM |
| Executive dashboard approval reminder | Metasheet | Notification/orchestration layer only |

## PR Review Questions

Every workflow-related change should answer these questions explicitly:

1. Does this workflow touch `item`, `BOM`, `version`, `ECO`, `approval`, or `release` state?
2. If yes, which Yuantus endpoint is the system of record?
3. If no, why is this a non-PLM workflow?
4. Is Metasheet being used only as UI/orchestration, or is it incorrectly taking ownership of PLM state?
5. Has the counterpart team reviewed the boundary change?

## Allowed Patterns

- Metasheet calls Yuantus approval endpoints and renders a richer inbox.
- Yuantus exposes release and approval APIs while Metasheet provides dashboards.
- Metasheet hosts external forms that submit into Yuantus-owned approval processes.

## Forbidden Patterns

- Metasheet directly invents a second approval source of truth for PLM objects.
- Yuantus grows generic HR, finance, or non-PLM workflow features.
- Either system bypasses the other system's agreed source of truth for convenience.

## Repository Policy Follow-Up

This ruleset should be mirrored into contributor guidance:

- [CONTRIBUTING.md](/Users/huazhou/Downloads/Github/Yuantus/CONTRIBUTING.md) in Yuantus
- `CONTRIBUTING.md` in Metasheet when that repo adds one

Until then, reviewers should link this file directly in workflow-related PRs.
