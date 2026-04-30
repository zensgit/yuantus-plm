# Development Task — Phase 3 Tenant Import Stop-Gate Contracts

Date: 2026-04-30

## 1. Objective

Add lightweight contracts that prevent the synthetic drill from being treated as
operator-run PostgreSQL rehearsal evidence.

This is a guardrail PR after the synthetic drill landed. It protects the P3.4
stop gate from accidental checklist drift.

## 2. Scope

Add one contract test file:

- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`

The contracts must pin:

- parent P3.4 TODO keeps real operator evidence unchecked;
- runbook says synthetic output is not operator-run evidence;
- synthetic drill runtime report keeps evidence and cutover gates closed;
- synthetic drill source does not import real archive or handoff gates;
- design and verification docs state the real evidence gap remains.

## 3. Non-Goals

This task must not:

- change runtime behavior;
- change the synthetic drill implementation;
- mark operator-run PostgreSQL evidence complete;
- open database connections;
- add production cutover logic;
- enable `TENANCY_MODE=schema-per-tenant`.

## 4. Acceptance Criteria

- New stop-gate contracts pass.
- Synthetic drill focused tests still pass.
- Full P3.4 focused suite still passes.
- Doc-index and runbook contracts pass.
- `git diff --check` is clean.

## 5. Stop Rule

If a future change makes synthetic output satisfy `ready_for_operator_evidence`,
`ready_for_evidence_handoff`, or `ready_for_cutover`, the contracts must fail.
