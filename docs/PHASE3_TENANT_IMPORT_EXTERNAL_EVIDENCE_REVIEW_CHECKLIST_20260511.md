# Phase 3 Tenant Import External Evidence Review Checklist

Date: 2026-05-11

## 1. Purpose

This checklist is for reviewers after an operator has produced real P3.4
non-production PostgreSQL rehearsal evidence.

It is not an operator runbook, not a replacement for
`docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`, and not an authorization to start
Phase 5 or production cutover.

## 2. Required Artifact Set

Review only a complete artifact set generated from real operator execution:

- `output/tenant_<tenant-id>_import_rehearsal.json`
- `output/tenant_<tenant-id>_import_rehearsal.md`
- `output/tenant_<tenant-id>_operator_rehearsal_evidence.md`
- `output/tenant_<tenant-id>_import_rehearsal_evidence.json`
- `output/tenant_<tenant-id>_import_rehearsal_evidence_archive.json`
- `output/tenant_<tenant-id>_redaction_guard.json`
- `output/tenant_<tenant-id>_evidence_handoff.json`
- `output/tenant_<tenant-id>_evidence_intake.json`
- `output/tenant_<tenant-id>_reviewer_packet.json`
- `output/tenant_<tenant-id>_reviewer_packet.md`

The reviewer packet is the entrypoint artifact. The other artifacts are the
evidence chain that must support it.

## 3. Acceptance Checks

All checks below must pass before P3.4 evidence can be marked accepted:

- [ ] `Ready for reviewer packet: true`
- [ ] `Ready for evidence intake: true`
- [ ] `Ready for evidence handoff: true`
- [ ] `Redaction ready: true`
- [ ] `Rehearsal import passed: true`
- [ ] `Import executed: true`
- [ ] `DB connection attempted: true`
- [ ] `Rehearsal evidence accepted: true`
- [ ] `Operator evidence accepted: true`
- [ ] All artifact blockers arrays are empty.
- [ ] Tenant id, target schema, and redacted target URL match across intake,
  handoff, and reviewer packet.
- [ ] Archive artifacts include SHA-256 digests.
- [ ] Intake artifacts do not include synthetic drill output.
- [ ] Every PostgreSQL URL in Markdown is redacted as
  `postgresql://<user>:***@<host>/<database>` or equivalent.

The following value must remain false everywhere it appears:

- [ ] `Ready for cutover: false`

## 4. Rejection Checks

Reject the evidence packet if any item below is true:

- Synthetic drill output is submitted as real evidence.
- `Ready for cutover: true` appears in any artifact.
- Any plaintext PostgreSQL password appears in JSON, Markdown, logs, or PR
  text.
- Source/target database context is missing or inconsistent.
- Reviewer packet was generated without green evidence-intake and
  evidence-handoff reports.
- Operator evidence has placeholder sign-off fields.
- Rehearsal output came from mock DSNs or a local-only drill.

## 5. Decision Boundary

If the packet passes review, record only this decision:

```text
P3.4 real non-production PostgreSQL rehearsal evidence accepted.
Ready for cutover remains false.
```

That decision may unblock a separate Phase 5 planning/implementation PR, but it
does not by itself:

- start Phase 5;
- enable runtime `TENANCY_MODE=schema-per-tenant`;
- authorize production cutover;
- authorize production data migration;
- authorize destructive cleanup or automatic rollback.

## 6. Reviewer Sign-Off Template

```text
Pilot tenant:
Reviewer:
Evidence packet path:
Review date:
Decision: accept | reject
Reason:
Ready for cutover confirmed false: yes | no
Plaintext secret scan clean: yes | no
Phase 5 follow-up PR required: yes | no
```

Keep this sign-off outside the repository if it contains environment names,
ticket IDs, or operational details that should not be public.
