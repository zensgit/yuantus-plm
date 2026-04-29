# Development Task - Phase 3 Tenant Import Rehearsal Toolchain Closeout

Date: 2026-04-29

## 1. Goal

Close out the P3.4 tenant import rehearsal toolchain documentation against the
current code state.

This is a documentation reconciliation task. It records that the DB-free and
guarded rehearsal tooling is implemented through the external status checker,
and that the remaining work is external operator execution.

## 2. Rationale

The parent P3.4 TODO still contained unchecked implementation-gate items that
are now enforced by the implementation packet and the row-copy rehearsal guard.
Leaving those unchecked makes the plan look like more local runtime code is
required before an operator can run the non-production rehearsal.

The current code state is different:

- `tenant_import_rehearsal_implementation_packet` validates handoff, plan,
  source preflight, target preflight, and next-action readiness.
- `tenant_import_rehearsal` revalidates the implementation packet and its
  upstream artifacts before opening database connections.
- `tenant_import_rehearsal_operator_packet` produces ordered operator commands.
- `tenant_import_rehearsal_external_status` reports the next external action
  without executing commands.

## 3. Scope

- Add this closeout task MD.
- Add a DEV/verification MD.
- Add a closeout TODO MD.
- Update the parent P3.4 TODO to reflect completed machine-gate requirements.
- Update `docs/DELIVERY_DOC_INDEX.md`.

## 4. Non-Goals

- No runtime-code changes.
- No database connections.
- No row-copy rehearsal execution.
- No operator evidence creation.
- No archive generation against real evidence.
- No production cutover.
- No `TENANCY_MODE=schema-per-tenant` enablement.

## 5. Current Toolchain State

Implemented and merged:

- dry-run report;
- readiness report;
- Claude handoff report;
- import plan;
- source preflight;
- target preflight;
- next-action report;
- implementation packet;
- packet integrity hardening;
- guarded row-copy rehearsal;
- operator evidence template;
- evidence gate;
- evidence archive manifest;
- operator execution packet;
- external status checker.

## 6. Remaining External Work

The following remain blocked on operator-provided inputs and execution:

- pilot tenant approval;
- non-production PostgreSQL rehearsal DSNs;
- backup/restore owner;
- rehearsal window;
- table classification sign-off;
- P3.4.1 dry-run report for the real source;
- real row-copy rehearsal;
- operator evidence;
- evidence gate report;
- archive manifest for the real evidence chain.

## 7. Acceptance Criteria

- Parent P3.4 TODO no longer shows completed machine gates as unchecked.
- Closeout docs clearly state that production cutover remains blocked.
- Documentation index stays sorted and complete.
- Doc-index contracts stay green.
- No runtime files are modified.
