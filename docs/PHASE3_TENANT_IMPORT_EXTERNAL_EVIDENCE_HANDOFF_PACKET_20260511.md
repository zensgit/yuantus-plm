# Phase 3 Tenant Import External Evidence Handoff Packet

Date: 2026-05-11

## 1. Purpose

This packet is the post-P6 handoff for the remaining P3.4 external evidence
gate.

It is for an external operator who will run a real non-production PostgreSQL
tenant-import rehearsal and generate reviewable evidence. It does not start
Phase 5, does not synthesize evidence, and does not authorize production
cutover.

## 2. Current State

- Prepared from `main=16c64f6`.
- Phase 4 search work is complete.
- Phase 6 circuit-breaker work is complete.
- Phase 5 provisioning/backup remains blocked.
- P3.4 remains blocked until real operator-run non-production PostgreSQL
  rehearsal evidence exists and is accepted.
- Runtime `TENANCY_MODE=schema-per-tenant` enablement remains not authorized.

## 3. Required External Inputs

All items below must be real operator inputs. Repository-local synthetic output
does not satisfy this gate.

- [ ] Named pilot tenant.
- [ ] Non-production PostgreSQL source DSN available outside the repository.
- [ ] Non-production PostgreSQL target DSN available outside the repository.
- [ ] Backup/restore owner named.
- [ ] Rehearsal window scheduled.
- [ ] Table classification artifact signed off.
- [ ] Evidence reviewer named.

Credentials must stay outside the repository. Any DSN included in Markdown or
reviewer artifacts must be redacted, for example
`postgresql://<user>:***@<host>/<database>`.

## 4. Canonical Operator Path

Use `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md` as the source of truth. The
shortest approved path is:

1. Generate a repo-external env-file template:

```bash
scripts/generate_tenant_import_rehearsal_env_template.sh \
  --out "$HOME/.config/yuantus/tenant-import-rehearsal.env"
```

2. Edit the env file outside the repository and fill real non-production
   source and target PostgreSQL DSNs.

3. Precheck the env file before any shell source or database action:

```bash
scripts/precheck_tenant_import_rehearsal_env_file.sh \
  --env-file "$HOME/.config/yuantus/tenant-import-rehearsal.env"
```

4. During the approved rehearsal window, run the full-closeout wrapper:

```bash
scripts/run_tenant_import_rehearsal_full_closeout.sh \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --artifact-prefix output/tenant_<tenant-id> \
  --backup-restore-owner "<owner>" \
  --rehearsal-window "<window>" \
  --rehearsal-executed-by "<operator>" \
  --evidence-reviewer "<reviewer>" \
  --date "<yyyy-mm-dd>" \
  --env-file "$HOME/.config/yuantus/tenant-import-rehearsal.env" \
  --confirm-rehearsal \
  --confirm-closeout
```

5. Review the generated evidence-intake, evidence-handoff, and reviewer-packet
   artifacts. The reviewer packet is the handoff artifact that can move P3.4
   from local-ready to evidence-review.

## 5. Acceptance Boundary

The evidence chain can be accepted only when all of these fields are true in
real operator-generated artifacts:

- `Import executed: true`
- `DB connection attempted: true`
- `Rehearsal evidence accepted: true`
- `Operator evidence accepted: true`
- `Ready for evidence intake: true`
- `Ready for evidence handoff: true`
- `Ready for reviewer packet: true`

The following field must remain false:

- `Ready for cutover: false`

## 6. Explicit Rejections

Do not accept any of these as P3.4 completion:

- Synthetic drill output.
- Local-only command-path rehearsal.
- Mock source or target DSNs.
- A reviewer packet generated from artifacts that did not connect to real
  non-production PostgreSQL databases.
- Any artifact containing plaintext PostgreSQL passwords.
- Any artifact that says `Ready for cutover: true`.

## 7. Next Decision After Evidence Review

If the reviewer accepts the real evidence packet, the next planning decision is
whether to open Phase 5 P5.1. Until that acceptance exists:

- Do not start Phase 5 implementation.
- Do not enable `TENANCY_MODE=schema-per-tenant`.
- Do not start production cutover.
- Do not ask Claude to fill missing evidence.

## 8. Reviewer Checklist

- Confirm real non-production PostgreSQL source and target databases were used.
- Confirm source/target DSNs are repo-external and redacted in all artifacts.
- Confirm the full-closeout wrapper was run with `--confirm-rehearsal` and
  `--confirm-closeout`.
- Confirm synthetic drill artifacts are not included as real evidence.
- Confirm the reviewer packet keeps `Ready for cutover: false`.
- Confirm Phase 5 remains blocked until evidence acceptance is recorded.
