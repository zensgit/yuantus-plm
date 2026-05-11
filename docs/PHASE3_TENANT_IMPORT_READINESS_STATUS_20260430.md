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
unsupported executable or option lines in generated command files before
operator use. Path-valued generated command options are now also limited to a
safe artifact path token set, so edited redirection, variable expansion, and
quoted path rewrites are rejected before operator use. Quoted generated evidence
metadata fields now also reject shell variable expansion and backslash escape
syntax before operator use. Shell syntax diagnostics from generated command-file
validation are redacted so raw `bash -n` error lines cannot echo edited command
content. Validator CLI parse errors also hide unknown argument values and
missing command-file paths. Env-file precheck CLI parse errors also hide
unknown argument values and missing env-file paths before any file is opened or
sourced. P3.4 shell wrapper CLI parse errors also hide unknown argument values
across env-template generation, operator precheck, command-pack preparation,
command printing, operator launchpack, operator sequence, full closeout,
evidence precheck, and evidence closeout entrypoints.

2026-05-06 update: the tenant import Python module CLIs now also hide
parse-time argument values. Unknown arguments for the rehearsal, preflight,
handoff, packet, evidence, synthetic drill, redaction guard, reviewer,
operator, and external-status modules emit fixed parse-failure markers instead
of raw `argparse` diagnostics.

2026-05-11 update: post-P6 external evidence handoff is now explicit through
two reviewable documents:

- `docs/PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_HANDOFF_PACKET_20260511.md`
  gives the operator the shortest approved path from repo-external env-file
  preparation through the full-closeout wrapper and evidence review.
- `docs/PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_REVIEW_CHECKLIST_20260511.md`
  gives reviewers the acceptance and rejection checklist for real
  non-production PostgreSQL rehearsal evidence.

These documents close the remaining local handoff/documentation gap only. They
do not provide operator-run PostgreSQL evidence, do not mark P3.4 complete, and
do not unblock Phase 5 without accepted real evidence.

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
- generated command-file option-line allowlist.
- generated command-file safe path option validation.
- generated command-file quoted metadata expansion guard.
- generated command-file shell syntax diagnostic redaction.
- generated command-file validator CLI error redaction.
- env-file precheck CLI error redaction.
- shell wrapper CLI error redaction.
- Python module CLI error redaction.
- post-P6 external evidence handoff packet.
- post-P6 external evidence reviewer checklist.

## 2. Blocked State

The remaining P3.4 blocker is external:

- operator-run PostgreSQL rehearsal evidence is not complete.
- reviewer acceptance of real operator-run evidence is not recorded.

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

The operator and reviewer must provide, run, or use:

- approved pilot tenant;
- non-production PostgreSQL rehearsal DSN;
- backup/restore owner;
- rehearsal window;
- signed table classification artifact;
- P3.4.1 dry-run report with `ready_for_import=true`;
- repo-external env-file generated from the template and statically prechecked;
- repo-external env-file contains only the selected source/target URL variables;
- generated operator command file that passes the command-file validator;
- generated command file whose path-valued options pass safe path validation;
- generated command file whose quoted metadata fields pass expansion-guard
  validation;
- generated command file whose shell syntax failure diagnostics stay redacted;
- generated command-file validator CLI errors do not echo argument values or
  missing command-file paths;
- env-file precheck CLI errors do not echo argument values or missing env-file
  paths;
- P3.4 shell wrapper CLI errors do not echo unknown argument values;
- P3.4 Python module CLI errors do not echo unknown argument values;
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
- external evidence handoff packet;
- external evidence reviewer checklist.

## 5. Reviewer Checklist

Before treating P3.4 as rehearsal-complete, reviewers should require:

- real row-copy report with `import_executed=true`;
- real operator evidence Markdown with non-placeholder sign-off fields;
- archive manifest with artifact hashes;
- redaction guard with complete artifact coverage;
- env-file precheck, command-file validation, and wrapper safety contracts green;
- env-file key allowlist coverage for command-pack and full-closeout wrappers;
- command-file executable-line allowlist coverage;
- command-file option-line allowlist coverage;
- command-file safe path option coverage for redirection, variable expansion,
  and quoted path rewrites;
- command-file quoted metadata coverage for shell variable expansion and
  backslash escape syntax;
- command-file shell syntax diagnostic redaction coverage;
- command-file validator CLI error redaction coverage;
- env-file precheck CLI error redaction coverage;
- shell wrapper CLI error redaction coverage;
- Python module CLI error redaction coverage;
- evidence intake report with `ready_for_evidence_intake=true`;
- evidence handoff report with `ready_for_evidence_handoff=true`;
- reviewer packet with `ready_for_reviewer_packet=true`;
- review checklist decision that accepts real operator evidence;
- all reports still showing `ready_for_cutover=false`.

## 6. Engineering Recommendation

Do not add local bypass tooling for P3.4. DB-free safety hardening is acceptable
only when it reduces operator risk without simulating evidence or changing the
external stop gate.

After real rehearsal evidence exists and passes reviewer checklist acceptance,
the next engineering PR should be a small final signoff PR that records the
real evidence artifact digests and preserves the cutover block. Phase 5 should
start only after that signoff records accepted evidence.

## 7. Verification Anchor

The closeout contract for this status lives in:

```text
src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py
```
