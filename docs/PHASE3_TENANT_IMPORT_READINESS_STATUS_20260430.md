# Phase 3 Tenant Import Readiness Status

Date: 2026-04-30

## 1. Current State

P3.4 tenant import rehearsal is locally ready through reviewer packet.

The repository now includes DB-free gates and handoff tools for:

- dry-run readiness;
- Claude implementation handoff;
- import plan;
- source and target preflight;
- implementation packet;
- guarded row-copy rehearsal;
- operator evidence template;
- evidence validation;
- archive manifest;
- redaction guard;
- evidence handoff;
- evidence intake checklist;
- reviewer packet;
- synthetic drill for command-path rehearsal.

2026-05-05 update: the local operator handoff path also includes repo-external
env-file template generation, env-file precheck, command-pack generation,
command-file validation, and full-closeout wrapper support. The latest safety
hardening keeps these gates DB-free while rejecting unsafe env-file syntax and
out-of-order generated command files. It now also rejects env-file keys outside
the selected source/target URL variables before any shell source operation and
unsupported executable lines in generated command files before operator use.

The 2026-05-05 safety closeout is tracked as completed for local tooling only:

- repo-external env-file template generation;
- DB-free env-file static precheck before shell source;
- env-file support in operator command pack and full-closeout wrappers;
- generated operator command-file validation;
- command-file and env-file source safety hardening;
- wrapper-level unsafe env-file source guard contracts;
- runbook operator safety contracts.
- source/target URL env-name allowlist hardening.
- env-file key allowlist before shell source.
- generated command-file executable-line allowlist.

## 2. Blocked State

The remaining P3.4 blocker is external:

- operator-run PostgreSQL rehearsal evidence is not complete.

The parent TODO intentionally still says:

```text
- [ ] Add operator-run PostgreSQL rehearsal evidence.
```

## 3. Not Authorized

This status does not authorize:

- production cutover;
- runtime `TENANCY_MODE=schema-per-tenant` enablement;
- data import into any production database;
- automatic rollback or destructive cleanup.

Every P3.4 artifact produced by the current toolchain must keep
`ready_for_cutover=false`.

## 4. Next Valid Action

The next valid action is external operator execution using
`docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`.

The operator must provide or run:

- approved pilot tenant;
- non-production PostgreSQL rehearsal DSN;
- backup/restore owner;
- rehearsal window;
- signed table classification artifact;
- P3.4.1 dry-run report with `ready_for_import=true`;
- repo-external env-file generated from the template and statically prechecked;
- repo-external env-file contains only the selected source/target URL variables;
- generated operator command file that passes the command-file validator;
- full-closeout wrapper using the prechecked env-file path;
- uppercase source/target URL env-var names when overriding defaults;
- row-copy rehearsal;
- operator evidence;
- evidence gate;
- archive manifest;
- redaction guard;
- evidence handoff gate;
- evidence intake checklist;
- reviewer packet.

## 5. Reviewer Checklist

Before treating P3.4 as rehearsal-complete, reviewers should require:

- real row-copy report with `import_executed=true`;
- real operator evidence Markdown with non-placeholder sign-off fields;
- archive manifest with artifact hashes;
- redaction guard with complete artifact coverage;
- env-file precheck, command-file validation, and wrapper safety contracts green;
- env-file key allowlist coverage for command-pack and full-closeout wrappers;
- command-file executable-line allowlist coverage;
- evidence intake report with `ready_for_evidence_intake=true`;
- evidence handoff report with `ready_for_evidence_handoff=true`;
- reviewer packet with `ready_for_reviewer_packet=true`;
- all reports still showing `ready_for_cutover=false`.

## 6. Engineering Recommendation

Do not add local bypass tooling for P3.4. DB-free safety hardening is acceptable
only when it reduces operator risk without simulating evidence or changing the
external stop gate.

After real rehearsal evidence exists, the next engineering PR should be a small
final signoff PR that records the real evidence artifact digests and preserves
the cutover block.

## 7. Verification Anchor

The closeout contract for this status lives in:

```text
src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py
```
