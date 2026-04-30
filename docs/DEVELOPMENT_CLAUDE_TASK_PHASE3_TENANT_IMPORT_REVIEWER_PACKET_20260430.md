# Development Task — Phase 3 Tenant Import Reviewer Packet

Date: 2026-04-30

## 1. Objective

Add a DB-free reviewer packet for P3.4.2 tenant import rehearsal artifacts.

The packet is generated only after the evidence intake checklist and evidence
handoff gate are both green. It gives reviewers a single summary entry point
without accepting evidence or authorizing cutover.

## 2. Scope

Implement one new script:

- `src/yuantus/scripts/tenant_import_rehearsal_reviewer_packet.py`

Inputs:

- evidence intake JSON;
- evidence handoff JSON.

Outputs:

- reviewer packet JSON;
- reviewer packet Markdown.

## 3. Required Checks

The script must:

- validate evidence intake schema version;
- require `ready_for_evidence_intake=true`;
- require `redaction_ready=true`;
- require evidence intake blockers to be empty;
- validate evidence handoff schema version;
- require `ready_for_evidence_handoff=true`;
- require evidence handoff blockers to be empty;
- require `tenant_id`, `target_schema`, and `target_url` to match;
- keep `ready_for_cutover=false`.

## 4. Non-Goals

This task must not:

- open database connections;
- run rehearsal commands;
- accept operator evidence;
- build archive manifests;
- run cutover;
- enable runtime schema-per-tenant mode.

## 5. Output Files

- `src/yuantus/scripts/tenant_import_rehearsal_reviewer_packet.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_reviewer_packet.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_REVIEWER_PACKET_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_REVIEWER_PACKET_TODO_20260430.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_REVIEWER_PACKET_20260430.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 6. Acceptance Criteria

- Green intake + green handoff builds a reviewer packet.
- Blocked intake blocks the reviewer packet.
- Blocked handoff blocks the reviewer packet.
- Context mismatch blocks the reviewer packet.
- Upstream `ready_for_cutover=true` blocks the reviewer packet.
- CLI strict mode exits 1 when blocked.
- Full P3.4 focused suite remains green.

## 7. Stop Rule

If the reviewer packet starts accepting evidence, creating evidence, building an
archive, or authorizing cutover, stop and split that into a separately reviewed
phase.
