# Runbook — Tenant Schema Provisioning and Migration (2026-04-27)

## 1. Scope

This runbook covers operator actions for schema-per-tenant preparation, post P3.3.3 baseline revision:

- Resolve the managed schema name for a tenant id.
- Provision the tenant schema out of band.
- Generate tenant Alembic offline SQL for review.
- Apply the tenant Alembic baseline revision so tenant application tables exist inside the target schema.

This runbook does not authorize runtime cutover, data migration, or production enablement.

## 2. Prerequisites

- P3.3.1 tenant Alembic env is merged.
- `DATABASE_URL` points at a non-production PostgreSQL database for rehearsal.
- `TENANCY_MODE` remains `single` unless a later P3.4 cutover explicitly changes it.
- Operator has an approved tenant id and a named reviewer for offline SQL.

## 3. Resolve Schema

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_schema resolve --tenant-id=<tenant-id>
```

Expected output:

```text
yt_t_<sanitized_tenant>
```

Stop if the output does not match the approved tenant record.

## 4. Provision Schema

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  python -m yuantus.scripts.tenant_schema create --tenant-id=<tenant-id>
```

The helper is idempotent and only issues `CREATE SCHEMA IF NOT EXISTS`.

It does not change privileges, ownership, tenant roles, or runtime settings.

## 5. Generate Offline SQL

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  upgrade head --sql > tenant_<schema>_<timestamp>.sql
```

Reviewer checklist:

- The first non-comment, non-blank SQL line is `SET search_path TO "<schema>", public;`.
- No DDL appears before that `SET search_path` line.
- `alembic_version` is targeted at the tenant schema.
- No global/control-plane table DDL appears for `auth_*`, `audit_logs`, `rbac_*`, or `users`.

Post-P3.3.3, this SQL contains the actual `CREATE TABLE` baseline DDL for tenant application tables. The reviewer must confirm the absence of any `auth_*`, `audit_logs`, `rbac_*`, and `users` table DDL — those tables remain on the global identity plane and must not appear here.

## 6. P3.4.1 Read-Only Source Dry Run

Before any import rehearsal, inspect the source database without touching a
target schema:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_migration_dry_run \
  --source-url <source-db-url> \
  --tenant-id <tenant-id> \
  --output-json output/tenant_<tenant-id>_dry_run.json \
  --output-md output/tenant_<tenant-id>_dry_run.md
```

Use `--strict` in CI or rehearsal automation when blockers should fail the
command:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_migration_dry_run \
  --source-url <source-db-url> \
  --tenant-id <tenant-id> \
  --output-json output/tenant_<tenant-id>_dry_run.json \
  --output-md output/tenant_<tenant-id>_dry_run.md \
  --strict
```

The dry-run report includes the FK-safe tenant import order, source table
inventory, tenant-table row counts, missing tenant tables, excluded global
tables, and unknown source tables. It never accepts a target DSN, never creates
schemas, and never exports or imports rows.

Do not proceed to import rehearsal while `ready_for_import` is false.

This dry run does not satisfy the external P3.4 stop-gate items by itself; the
pilot tenant, non-production PostgreSQL DSN, backup/restore owner, rehearsal
window, and classification sign-off are still required.

## 7. P3.4.2 Import Rehearsal Readiness

Before implementing or running import rehearsal tooling, validate the external
stop-gate inputs and P3.4.1 dry-run report without opening database
connections:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_readiness \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --tenant-id <tenant-id> \
  --target-url <non-prod-postgres-dsn> \
  --target-schema <schema> \
  --backup-restore-owner <owner> \
  --rehearsal-window <window> \
  --classification-artifact docs/TENANT_TABLE_CLASSIFICATION_20260427.md \
  --classification-signed-off \
  --output-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_readiness.md \
  --strict
```

Do not implement or run import rehearsal while
`ready_for_rehearsal` is false.

The `--classification-signed-off` flag is not sufficient by itself. The
validator also parses `docs/TENANT_TABLE_CLASSIFICATION_20260427.md` §6 and
requires the Sign-Off block to contain non-placeholder values for:

- `Pilot tenant`
- `PostgreSQL rehearsal DSN`
- `Backup/restore owner`
- `Rehearsal window`
- `Reviewer`
- `Decision`
- `Date`

The tracked document must use a redacted PostgreSQL DSN, for example
`postgresql://user:***@host/db`; never put a plaintext password in the
classification artifact. The validator compares this redacted DSN, the pilot
tenant, backup/restore owner, and rehearsal window with the CLI inputs before
setting `ready_for_rehearsal=true`.

## 8. P3.4.2 Claude Implementation Handoff

Claude can start implementing the actual rehearsal importer only after the
readiness report is green and the handoff generator produces a green task
packet:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_handoff \
  --readiness-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --output-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --output-md output/tenant_<tenant-id>_claude_import_rehearsal_task.md \
  --strict
```

The command must exit 0 and the generated Markdown must say:

```text
Claude can start: `true`
```

If the command exits 1, do not ask Claude to implement
`yuantus.scripts.tenant_import_rehearsal`; resolve the blockers in the handoff
report first.

The handoff generator does not open database connections and does not authorize
production cutover. It only converts verified readiness evidence into a bounded
Claude task packet.

## 9. P3.4.2 Import Rehearsal Plan

Before asking Claude to implement the importer, freeze the table-level plan
derived from the dry-run and handoff artifacts:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_plan \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --handoff-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_plan.md \
  --strict
```

The command must exit 0 and set `ready_for_importer=true`. It does not open
database connections; it pins the import order, source row-count expectations,
and global/control-plane table skip list. `ready_for_cutover` must stay false.

If the command exits 1, do not ask Claude to implement the importer. Fix the
plan blockers first.

## 10. P3.4.2 Source Preflight

Before asking Claude to implement the importer, run a read-only source schema
preflight:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_source_preflight \
  --plan-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --source-url <source-db-url> \
  --output-json output/tenant_<tenant-id>_source_preflight.json \
  --output-md output/tenant_<tenant-id>_source_preflight.md \
  --confirm-source-preflight \
  --strict
```

The command must exit 0 and set `ready_for_importer_source=true`. It validates
that the planned tenant tables exist in the source DB and that required target
metadata columns are present. It does not read rows, export rows, connect to a
target DB, or authorize cutover.

If the command exits 1, do not ask Claude to implement the importer. Fix the
source preflight blockers first.

## 11. Apply Baseline Upgrade

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  upgrade head
```

Expected behavior post-P3.3.3: the command applies the baseline revision (`t1_initial_tenant_baseline`) inside `<schema>`, creating tenant application tables and the per-tenant `<schema>.alembic_version` row. Cross-schema FKs to global tables (e.g., `rbac_users`, `users`) are intentionally NOT created — tenant tables retain user-attribution columns (`created_by_id`, `owner_id`, etc.) without a database-level FK constraint, since the referenced rows live in the global identity plane.

## 12. Smoke

Confirm the schema exists, that the baseline revision is recorded, and that representative tenant tables are present:

```sql
select nspname from pg_namespace where nspname = '<schema>';

select version_num from "<schema>"."alembic_version";
-- expect: t1_initial_tenant_baseline

select count(*) from information_schema.tables
where table_schema = '<schema>' and table_name in ('meta_items', 'meta_files', 'meta_conversion_jobs');
-- expect: 3

-- Negative smoke: no global tables in the tenant schema
select count(*) from information_schema.tables
where table_schema = '<schema>'
  and table_name in ('auth_users', 'rbac_users', 'users', 'audit_logs');
-- expect: 0
```

## 13. P3.4.2 Target Preflight

Before asking Claude to implement the importer, run a read-only target schema
preflight against the non-production PostgreSQL rehearsal database:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_target_preflight \
  --plan-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --target-url <non-prod-postgres-dsn> \
  --target-schema <schema> \
  --output-json output/tenant_<tenant-id>_target_preflight.json \
  --output-md output/tenant_<tenant-id>_target_preflight.md \
  --confirm-target-preflight \
  --strict
```

The command must exit 0 and set `ready_for_importer_target=true`. It validates
the target schema, `<schema>.alembic_version`, expected tenant table presence,
and the absence of global/control-plane tables. It does not create schemas,
apply migrations, import rows, or authorize cutover.

If the command exits 1, do not ask Claude to implement the importer. Fix the
target preflight blockers first.

## 14. P3.4.2 Next Action / Claude Notification

Use this command when you need a single status artifact that says what to do
next and whether Claude should start implementation:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_next_action \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --readiness-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --handoff-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --plan-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --source-preflight-json output/tenant_<tenant-id>_source_preflight.json \
  --target-preflight-json output/tenant_<tenant-id>_target_preflight.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_next_action.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_next_action.md \
  --strict
```

The command returns 0 in `--strict` mode only when the next action is to ask
Claude to implement the importer. Otherwise it writes blockers and returns 1.

Notify the user that Claude development is needed only when the generated
report says:

```text
claude_required=true
next_action=ask_claude_to_implement_importer
```

## 15. P3.4.2 Claude Importer Implementation Packet

After next-action is green, generate the final Claude implementation packet:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_implementation_packet \
  --next-action-json output/tenant_<tenant-id>_import_rehearsal_next_action.json \
  --output-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --output-md output/tenant_<tenant-id>_claude_importer_task.md \
  --strict
```

Pass the generated Markdown to Claude only when it says:

```text
Claude can implement importer: `true`
```

The packet generator does not connect to any database and does not authorize
production cutover. It only converts the full green evidence chain into a
bounded implementation task for `yuantus.scripts.tenant_import_rehearsal`.

The packet generator also re-opens every upstream JSON artifact referenced by
next-action and blocks if any file is missing, has the wrong schema version, is
not ready, contains blockers, or disagrees with the next-action tenant/schema
context. Do not hand the Markdown to Claude unless the `Artifact Integrity`
table shows every ready value as `true`.

## 16. P3.4.2 Operator Execution Packet

Before running the row-copy rehearsal, generate a DB-free operator execution
packet with the exact command sequence and output paths:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_operator_packet \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --artifact-prefix output/tenant_<tenant-id> \
  --output-json output/tenant_<tenant-id>_operator_execution_packet.json \
  --output-md output/tenant_<tenant-id>_operator_execution_packet.md \
  --strict
```

The packet must say:

```text
Ready for operator execution: `true`
Ready for cutover: `false`
```

This packet does not run any command, open any database connection, or authorize
production cutover. It only consolidates the row-copy, operator-evidence,
evidence-gate, and archive-manifest commands into one reviewable handoff.

## 17. P3.4.2 External Status Check

Before and after each external operator action, run the DB-free status checker:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_external_status \
  --operator-packet-json output/tenant_<tenant-id>_operator_execution_packet.json \
  --output-json output/tenant_<tenant-id>_external_status.json \
  --output-md output/tenant_<tenant-id>_external_status.md \
  --strict
```

The status report must keep:

```text
Ready for external progress: `true`
Ready for cutover: `false`
```

Use `Current stage`, `Next action`, and `Next Command` from the Markdown report
to decide whether to run row-copy, generate operator evidence, run the evidence
gate, or build the archive manifest. Missing future artifacts are normal pending
state; malformed existing artifacts are blockers.

The status checker reads files only. It does not run any command, open any
database connection, accept evidence, build an archive, or authorize production
cutover.

### 17.1 P3.4.2 Operator Request Packet

To hand the current external-status result to an operator without asking them
to re-derive the next action from JSON, generate a DB-free operator request:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_operator_request \
  --external-status-json output/tenant_<tenant-id>_external_status.json \
  --output-json output/tenant_<tenant-id>_operator_request.json \
  --output-md output/tenant_<tenant-id>_operator_request.md \
  --strict
```

The request must say:

```text
Ready for operator request: `true`
Ready for cutover: `false`
```

The Markdown lists the current stage, required operator inputs, artifact
summary, and the exact next command from the external-status report. It does
not run that command, open database connections, accept evidence, build an
archive, authorize production cutover, or enable runtime schema-per-tenant mode.

### 17.2 P3.4.2 Operator Bundle

To reduce operator handoff friction, convert the operator request into a
single DB-free execution bundle:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_operator_bundle \
  --operator-request-json output/tenant_<tenant-id>_operator_request.json \
  --output-json output/tenant_<tenant-id>_operator_bundle.json \
  --output-md output/tenant_<tenant-id>_operator_bundle.md \
  --strict
```

The bundle must say:

```text
Ready for operator bundle: `true`
Ready for cutover: `false`
```

For command stages, the Markdown lists safety reminders, required inputs,
environment checks, and the exact next command. For `rehearsal_archive_ready`,
the bundle emits a manual-review instruction instead of inventing a command.

The bundle reads the operator request only. It does not run commands, open
database connections, accept evidence, build an archive, authorize production
cutover, or enable runtime schema-per-tenant mode.

### 17.3 P3.4.2 Operator Flow

To generate the external status, operator request, and operator bundle in one
DB-free step, run:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_operator_flow \
  --operator-packet-json output/tenant_<tenant-id>_operator_execution_packet.json \
  --artifact-prefix output/tenant_<tenant-id>_operator_flow \
  --output-json output/tenant_<tenant-id>_operator_flow.json \
  --output-md output/tenant_<tenant-id>_operator_flow.md \
  --strict
```

The flow report must say:

```text
Ready for operator flow: `true`
Ready for cutover: `false`
```

The command writes six handoff artifacts:

- external status JSON/Markdown;
- operator request JSON/Markdown;
- operator bundle JSON/Markdown.

Use the generated operator bundle Markdown as the execution handoff. The flow
reads local artifacts and writes reports only. It does not run rehearsal
commands, open database connections, accept evidence, build an archive,
authorize production cutover, or enable runtime schema-per-tenant mode.

### 17.4 P3.4.2 Operator Launchpack

To print the full operator command sequence from launchpack through evidence
closeout without executing it, run:

```bash
scripts/print_tenant_import_rehearsal_commands.sh \
  --artifact-prefix output/tenant_<tenant-id> \
  --env-file "$HOME/.config/yuantus/tenant-import-rehearsal.env"
```

Review the printed commands before execution. The helper now includes the
repo-external env-file template generation step, the env-file precheck, and a
safe `set -a; . <env-file>; set +a` load before row-copy. It never reads or
displays secret URL values.

Before executing the printed commands, run the DB-free precheck:

```bash
scripts/precheck_tenant_import_rehearsal_operator.sh \
  --artifact-prefix output/tenant_<tenant-id>
```

The precheck confirms the implementation packet is green, the helper scripts
exist, and `SOURCE_DATABASE_URL` / `TARGET_DATABASE_URL` are set. It reports
only environment variable names and never prints the secret URL values.

To generate the operator execution packet plus the full operator flow from the
implementation packet in one DB-free step, run:

```bash
scripts/run_tenant_import_operator_launchpack.sh \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --artifact-prefix output/tenant_<tenant-id>
```

The shell entrypoint derives the standard output paths. It is strict by default
and exits non-zero if the launchpack is blocked.

Equivalent explicit Python invocation:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_operator_launchpack \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --artifact-prefix output/tenant_<tenant-id> \
  --operator-packet-json output/tenant_<tenant-id>_operator_execution_packet.json \
  --operator-packet-md output/tenant_<tenant-id>_operator_execution_packet.md \
  --flow-artifact-prefix output/tenant_<tenant-id>_operator_flow \
  --output-json output/tenant_<tenant-id>_operator_launchpack.json \
  --output-md output/tenant_<tenant-id>_operator_launchpack.md \
  --strict
```

The launchpack report must say:

```text
Ready for operator launchpack: `true`
Ready for cutover: `false`
```

The command writes the operator execution packet, external status, operator
request, operator bundle, and launchpack summary. Use this command when the
operator starts from a green implementation packet and wants all DB-free
handoff artifacts prepared at once.

The launchpack reads local artifacts and writes reports only. It does not run
rehearsal commands, open database connections, accept evidence, build an
archive, authorize production cutover, or enable runtime schema-per-tenant
mode.

## 17.1 P3.4.2 Operator Command Pack

Before running row-copy, generate the operator command file through the
precheck-gated wrapper:

```bash
scripts/prepare_tenant_import_rehearsal_operator_commands.sh \
  --artifact-prefix output/tenant_<tenant-id> \
  --output output/tenant_<tenant-id>_operator_commands.sh \
  --env-file "$HOME/.config/yuantus/tenant-import-rehearsal.env" \
  --source-url-env SOURCE_DATABASE_URL \
  --target-url-env TARGET_DATABASE_URL
```

The wrapper first runs the DB-free env-file precheck and then the DB-free
operator precheck. If the implementation packet is missing, the packet is not
green, the env file is missing, placeholders remain, or the source/target DSN
variables are not set after loading the env file, the wrapper exits non-zero
and does not write the command file.

The env-file precheck validates the file statically before loading it. Only
comments, blank lines, and static assignments for the selected source/target URL
variables are allowed. Extra keys such as `PATH`, `PYTHON`, `PYTHONPATH`, and
`BASH_ENV` are rejected before the file is sourced. Command substitution, shell
expansion syntax, double-quoted values, and non-assignment lines are also
rejected before the file is sourced.

Custom `--source-url-env` and `--target-url-env` values must be uppercase shell
environment variable names matching `[A-Z_][A-Z0-9_]*`. Invalid names are
rejected before any env file is sourced, before indirect environment expansion,
and before generated operator commands are written.

The generated command file contains environment variable placeholders only. It
does not contain secret DSN values and does not authorize cutover.

The wrapper validates the generated command file before returning success. The
command-file validator checks shell syntax, required step order, environment
variable URL references with uppercase shell variable names, and forbidden
DSN/cutover/remote-control patterns. It also rejects unsupported executable
lines, so an edited command file cannot add extra `rm`, `ssh`, `python -c`,
`export`, or shell-control lines and still pass validation. Continuation option
lines are also checked against the generated command step they belong to; an
edited command file cannot add unknown options such as `--confirm-cutover`, move
`--output-json` into the env precheck step, or append orphan option lines and
still pass validation. Path-valued option arguments are restricted to a safe
artifact path token set (`[-A-Za-z0-9_./:]+`), so redirection, variable
expansion, and quoted path rewrites such as `>`, `<`, `$HOME`, or `"path"` are
rejected without echoing the edited value. Quoted evidence metadata fields are
also checked for shell expansion and escape syntax; values such as
`"$SOURCE_DATABASE_URL"` or `"ops\reviewer"` are rejected before operator use
without echoing the edited value. To revalidate the file later without executing
it, run:

```bash
scripts/validate_tenant_import_rehearsal_operator_commands.sh \
  --command-file output/tenant_<tenant-id>_operator_commands.sh
```

## 17.2 P3.4.2 Operator Sequence Wrapper

When the operator is ready to run the real non-production rehearsal, use the
single explicit sequence wrapper:

```bash
scripts/run_tenant_import_rehearsal_operator_sequence.sh \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --artifact-prefix output/tenant_<tenant-id> \
  --backup-restore-owner "<owner>" \
  --rehearsal-window "<window>" \
  --rehearsal-executed-by "<operator>" \
  --evidence-reviewer "<reviewer>" \
  --date "<yyyy-mm-dd>" \
  --confirm-rehearsal
```

The wrapper runs the operator precheck, launchpack, guarded row-copy,
operator-evidence template, and evidence precheck. It reads
`SOURCE_DATABASE_URL` and `TARGET_DATABASE_URL` by default, but prints only
environment variable names and local artifact paths.

This wrapper does not run evidence closeout. After it prints
`Ready for evidence closeout: true`, run the evidence closeout wrapper in the
next section.

## 17.3 P3.4.2 Full Closeout Wrapper

If the rehearsal window allows a single operator command from row-copy through
reviewer-packet generation, use the full-closeout wrapper:

First generate a repo-external env-file template if one does not already exist:

```bash
scripts/generate_tenant_import_rehearsal_env_template.sh \
  --out "$HOME/.config/yuantus/tenant-import-rehearsal.env"
```

Edit the generated file locally and replace the placeholders with real
non-production source and target PostgreSQL DSNs. The generator writes
placeholder values only, sets file mode 0600, and refuses to overwrite an
existing file unless `--force` is passed.

Before running the full-closeout wrapper, validate the file without connecting
to either database:

```bash
scripts/precheck_tenant_import_rehearsal_env_file.sh \
  --env-file "$HOME/.config/yuantus/tenant-import-rehearsal.env"
```

The full-closeout wrapper also runs this precheck automatically before any
row-copy command is invoked.

The precheck rejects env files that contain unsupported variables, shell
expansion syntax, double quotes, or non-assignment commands before the file is
sourced. Keep DSN values in single-quoted assignments for only the selected
source and target URL variables.

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

The wrapper runs the operator sequence, then evidence closeout. It still reads
database URLs from `SOURCE_DATABASE_URL` and `TARGET_DATABASE_URL`, can load
those variables from a repo-external env file, does not print their values, and
keeps `Ready for cutover: false`.

Example repo-external env file:

```bash
SOURCE_DATABASE_URL='postgresql://source-user:...@source-host/source-db'
TARGET_DATABASE_URL='postgresql://target-user:...@target-host/target-db'
```

Keep the file outside the repository and never commit it. The wrapper exports
variables from the file only for the child operator sequence and evidence
closeout process.

Use this wrapper only when the operator intends to proceed directly from real
rehearsal execution to local evidence closeout artifacts.

## 18. P3.4.2 Tenant Import Rehearsal Row Copy

After the implementation packet is green, run the guarded row-copy rehearsal:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --source-url "$SOURCE_DATABASE_URL" \
  --target-url "$TARGET_DATABASE_URL" \
  --output-json output/tenant_<tenant-id>_import_rehearsal.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal.md \
  --confirm-rehearsal \
  --strict
```

The command revalidates the implementation packet and all upstream JSON
artifacts before opening any database connection. It then copies only the
tenant application tables listed by `tenant_tables_in_import_order` and writes a
JSON/Markdown report with table-level row counts.

Do not treat this as production cutover. The report must say:

```text
Scaffold guard passed: `true`
Rehearsal import passed: `true`
Import executed: `true`
DB connection attempted: `true`
Ready for cutover: `false`
```

The command must not import any global/control-plane table, must not create or
migrate schemas, and must not enable `TENANCY_MODE=schema-per-tenant`.

## 19. P3.4.2 Rehearsal Evidence Gate

After the row-copy command finishes, capture the operator evidence in a local
Markdown file. Keep credentials out of the file; use the redacted target URL.
Prefer generating the correctly formatted Markdown from the row-copy report:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_template \
  --rehearsal-json output/tenant_<tenant-id>_import_rehearsal.json \
  --backup-restore-owner "<owner>" \
  --rehearsal-window "<window>" \
  --rehearsal-executed-by "<operator>" \
  --rehearsal-result pass \
  --evidence-reviewer "<reviewer>" \
  --date "<yyyy-mm-dd>" \
  --output-json output/tenant_<tenant-id>_operator_rehearsal_evidence_template.json \
  --output-md output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --strict
```

The generated Markdown has this sign-off shape:

````markdown
# Tenant Import Rehearsal Operator Evidence

## Rehearsal Evidence Sign-Off

```text
Pilot tenant: <tenant-id>
Non-production rehearsal DB: postgresql://<user>:***@<host>/<database>
Backup/restore owner: <owner>
Rehearsal window: <window>
Rehearsal executed by: <operator>
Rehearsal result: pass
Evidence reviewer: <reviewer>
Date: <yyyy-mm-dd>
```
````

Validate the rehearsal report, implementation packet, and operator evidence
without opening any database connection:

```bash
scripts/precheck_tenant_import_rehearsal_evidence.sh \
  --rehearsal-json output/tenant_<tenant-id>_import_rehearsal.json \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --operator-evidence-md output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --artifact-prefix output/tenant_<tenant-id>
```

This precheck writes:

```text
output/tenant_<tenant-id>_import_rehearsal_evidence.json
output/tenant_<tenant-id>_import_rehearsal_evidence.md
```

It exits non-zero if the real row-copy report is not green, the implementation
packet no longer validates, or the operator evidence Markdown has missing,
placeholder, or mismatched sign-off fields.

The underlying validator can also be run directly:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence \
  --rehearsal-json output/tenant_<tenant-id>_import_rehearsal.json \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --operator-evidence-md output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --output-json output/tenant_<tenant-id>_import_rehearsal_evidence.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_evidence.md \
  --strict
```

The evidence report must say:

```text
Rehearsal evidence accepted: `true`
Operator evidence accepted: `true`
Ready for cutover: `false`
```

This gate only proves that non-production rehearsal evidence is internally
consistent and reviewable. It does not authorize production cutover.

## 20. P3.4.2 Rehearsal Evidence Archive Manifest

After the evidence gate accepts the rehearsal output, the shortest closeout path
is the shell entrypoint:

```bash
scripts/run_tenant_import_evidence_closeout.sh \
  --evidence-json output/tenant_<tenant-id>_import_rehearsal_evidence.json \
  --operator-packet-json output/tenant_<tenant-id>_operator_execution_packet.json \
  --operator-evidence-template-json output/tenant_<tenant-id>_operator_rehearsal_evidence_template.json \
  --artifact-prefix output/tenant_<tenant-id>
```

The shell entrypoint builds the archive manifest, scans archived artifacts with
the redaction guard, validates the evidence handoff, runs the evidence intake
checklist, and emits the reviewer packet. It reads local artifacts only and is
strict by default.

Equivalent individual commands are listed below.

After the evidence gate accepts the rehearsal output, build a DB-free archive
manifest with SHA-256 digests for the full evidence chain:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_archive \
  --evidence-json output/tenant_<tenant-id>_import_rehearsal_evidence.json \
  --operator-evidence-template-json output/tenant_<tenant-id>_operator_rehearsal_evidence_template.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_evidence_archive.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_evidence_archive.md \
  --strict
```

If the operator evidence Markdown was hand-written instead of generated by the
template command, omit `--operator-evidence-template-json`.

The archive manifest must say:

```text
Ready for archive: `true`
Ready for cutover: `false`
```

This manifest is an integrity and handoff artifact only. It does not authorize
production cutover.

### 20.1 P3.4.2 Artifact Redaction Guard

Before handing rehearsal artifacts to reviewers or attaching them to a ticket,
scan the JSON/Markdown files for plaintext PostgreSQL passwords:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_redaction_guard \
  --artifact output/tenant_<tenant-id>_import_rehearsal.json \
  --artifact output/tenant_<tenant-id>_import_rehearsal.md \
  --artifact output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --artifact output/tenant_<tenant-id>_import_rehearsal_evidence.json \
  --artifact output/tenant_<tenant-id>_import_rehearsal_evidence_archive.json \
  --output-json output/tenant_<tenant-id>_redaction_guard.json \
  --output-md output/tenant_<tenant-id>_redaction_guard.md \
  --strict
```

The guard must say:

```text
Ready for artifact handoff: `true`
Ready for cutover: `false`
```

The report never prints the plaintext secret value. It reports only the artifact
path, line number, and redacted URL. If it fails, fix the artifact source before
sharing or archiving the files.

This guard reads local files only. It does not open database connections, run
rehearsal commands, accept evidence, build an archive, authorize production
cutover, or enable runtime schema-per-tenant mode.

### 20.2 P3.4.2 Evidence Handoff Gate

Before handing the archive to reviewers, tie the archive manifest to the
redaction guard and require redaction coverage for every archived artifact:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_handoff \
  --archive-json output/tenant_<tenant-id>_import_rehearsal_evidence_archive.json \
  --redaction-guard-json output/tenant_<tenant-id>_redaction_guard.json \
  --output-json output/tenant_<tenant-id>_evidence_handoff.json \
  --output-md output/tenant_<tenant-id>_evidence_handoff.md \
  --strict
```

The handoff gate must say:

```text
Ready for evidence handoff: `true`
Ready for cutover: `false`
```

This catches partial redaction scans: the guard fails unless every artifact
listed by the archive manifest also appears in the redaction guard report. It
does not open database connections, run rehearsal commands, accept new
evidence, build an archive, authorize production cutover, or enable runtime
schema-per-tenant mode.

### 20.3 P3.4.2 Evidence Intake Checklist

After the operator has generated the row-copy, evidence, and archive artifacts,
run a DB-free intake checklist before handing files to reviewers:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_intake \
  --operator-packet-json output/tenant_<tenant-id>_operator_execution_packet.json \
  --output-json output/tenant_<tenant-id>_evidence_intake.json \
  --output-md output/tenant_<tenant-id>_evidence_intake.md \
  --strict
```

The intake report must say:

```text
Ready for evidence intake: `true`
Ready for cutover: `false`
Redaction ready: `true`
```

The checklist verifies that the operator packet outputs exist, key JSON files
have the expected schema versions and ready fields, synthetic drill output is
not being submitted as real evidence, and the full artifact set is clean under
the redaction guard.

This checklist reads local files only. It does not open database connections,
run rehearsal commands, accept evidence, build an archive, run the evidence
handoff gate, authorize production cutover, or enable runtime schema-per-tenant
mode.

### 20.4 P3.4.2 Reviewer Packet

After both the evidence intake checklist and the evidence handoff gate are
green, generate a DB-free reviewer packet:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_reviewer_packet \
  --evidence-intake-json output/tenant_<tenant-id>_evidence_intake.json \
  --evidence-handoff-json output/tenant_<tenant-id>_evidence_handoff.json \
  --output-json output/tenant_<tenant-id>_reviewer_packet.json \
  --output-md output/tenant_<tenant-id>_reviewer_packet.md \
  --strict
```

The reviewer packet must say:

```text
Ready for reviewer packet: `true`
Ready for cutover: `false`
```

This packet consolidates the green intake and handoff summaries into one file
for reviewer handoff. It does not accept evidence, build an archive, run a
cutover, or enable runtime schema-per-tenant mode.

### 20.5 P3.4.2 Synthetic Operator Drill

Use the synthetic drill only to practice the local artifact and redaction
command path before real non-production PostgreSQL evidence exists:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_synthetic_drill \
  --artifact-dir output/tenant_<tenant-id>_synthetic_drill \
  --artifact-prefix tenant_<tenant-id>_synthetic_drill \
  --output-json output/tenant_<tenant-id>_synthetic_drill.json \
  --output-md output/tenant_<tenant-id>_synthetic_drill.md \
  --strict
```

The drill must say:

```text
Synthetic drill: `true`
Real rehearsal evidence: `false`
DB connection attempted: `false`
Ready for synthetic drill: `true`
Ready for operator evidence: `false`
Ready for evidence handoff: `false`
Ready for cutover: `false`
```

This output is not operator-run PostgreSQL rehearsal evidence. Do not attach it
as real evidence, do not feed it to the real archive or handoff gates, and do
not mark the P3.4 stop gate complete from synthetic output.

## 21. Rollback

This runbook performs no data migration; rollback is purely schema-level.

For per-schema rollback, use Alembic downgrade explicitly scoped to the target schema:

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  downgrade base
```

Downgrading the baseline (`t1_initial_tenant_baseline`) drops tenant application tables in reverse dependency order. The schema itself is left in place — schema removal is a separate operator action and is not exposed by this runbook.

Never run downgrade without `-x target_schema=<schema>`.

## 22. Stop Gate

Do not start P3.4 cutover (data migration / runtime enablement) until all are true:

- A named pilot tenant exists.
- Non-production rehearsal DB is available.
- Backup/restore owner is named.
- Rehearsal window is scheduled.
- P3.3.1, P3.3.2, and P3.3.3 are merged and smoke green.
- Table classification artifact is signed off.
