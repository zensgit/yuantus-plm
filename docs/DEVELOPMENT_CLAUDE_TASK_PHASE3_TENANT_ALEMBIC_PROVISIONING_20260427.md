# Development Plan — Phase 3 P3.3 Tenant Alembic + Provisioning Taskbook (2026-04-27)

## 1. Goal

Phase 3 P3.3 prepares the **migration plane** for `TENANCY_MODE=schema-per-tenant`
without enabling it in production and without moving data. P3.3 delivers:

1. A dedicated **tenant Alembic env** (`migrations_tenant/`) that applies tenant
   application tables to a per-tenant Postgres schema, with an isolated
   `alembic_version` table inside that schema.
2. A bounded **schema provisioning helper** (`CREATE SCHEMA IF NOT EXISTS …`)
   keyed off `tenant_id_to_schema()` from P3.2 — Postgres-only, idempotent,
   no role/grant changes.
3. A **migration safety / rollback / dry-run runbook** that pins the operational
   sequence operators must follow before any pilot rollout.

This document is the taskbook for P3.3.1 / P3.3.2. It does not add runtime
code, settings code, Alembic env files, provisioning scripts, or tests in this
PR.

P3.3 supersedes the P3.1 §5 recommendation of "Option 1 — tenant metadata
filter in the main env" in favour of **Option 2 — separate
`migrations_tenant/` env**, for the structural reasons given in §5.2 below.

## 2. Current Implementation Facts (post-P3.2 merge, `origin/main=80cc9dc`)

Evidence read before writing this taskbook:

| Area | Current state | Implication for P3.3 |
| --- | --- | --- |
| `src/yuantus/database.py` | `tenant_id_to_schema()` resolver, `_require_postgres_for_schema_mode()` guard, and `after_begin` schema dispatch in `get_db()` / `get_db_session()` are merged and default-off. | P3.3 reuses `tenant_id_to_schema()` as the single source of truth for schema name → no parallel resolver. |
| `migrations/env.py` lines 33–41 | Imports `AuthUser`, `Tenant`, `Organization`, `OrgMembership`, `TenantQuota`, `RBACUser`, `RBACRole` and combines `Base.metadata` + `WorkflowBase.metadata` into `combined_metadata` for `target_metadata`. | Running this env against a tenant schema would create identity tables inside that schema — explicitly forbidden by P3.1 §5. The main env must remain unchanged for global use; tenant migrations need a separate env. |
| `migrations_identity/env.py` lines 65–80 | Uses an explicit allowlist `IDENTITY_TABLE_NAMES = { auth_tenants, auth_organizations, auth_users, auth_credentials, auth_org_memberships, auth_tenant_quotas, audit_logs }` and copies only matching tables into `identity_metadata`. | The complement of this allowlist is the tenant table set. P3.3.1 mirrors this pattern with the inverse filter. |
| `src/yuantus/meta_engine/bootstrap.py` `import_all_models()` line 33 | Imports `yuantus.security.auth.models` — identity tables are registered in the combined metadata. | The tenant env must filter; it cannot rely on `import_all_models()` alone giving an identity-clean metadata. |
| `src/yuantus/security/auth/database.py` | Identity sessions route through `IDENTITY_DATABASE_URL` or base `DATABASE_URL`. | Identity plane stays untouched in P3.3. No identity Alembic changes. |
| `src/yuantus/config/settings.py` | `TENANCY_MODE` documents `schema-per-tenant`; no Alembic-target settings exist yet. | P3.3.1 introduces two new settings (default off, see §4.1). |

## 3. Target Semantics

### 3.1 What P3.3 enables

After P3.3 ships:

- An operator can call a small provisioning helper to issue `CREATE SCHEMA IF NOT EXISTS "yt_t_acme"` for a known tenant id.
- An operator can run `alembic -c alembic_tenant.ini -x target_schema=yt_t_acme upgrade head` against a non-production Postgres instance. Because `migrations_tenant/versions/` ships **empty by design** (see §3.3), `upgrade head` is a wiring exercise: the env validates target schema, applies `SET search_path`, configures `version_table_schema=yt_t_acme`, and exits cleanly with no DDL emitted. No tenant application tables are created.
- The runbook records the full safe sequence (provision → wiring smoke → review → apply (no-op until baseline revision lands) → smoke → leave runtime mode unchanged) and the rollback path.

### 3.2 What P3.3 does NOT enable

- **No tenant table baseline migration.** `migrations_tenant/versions/` is empty in the bounded P3.3 scope. The first autogenerate revision (which produces the actual `CREATE TABLE` DDL for tenant application tables) is deferred — see §3.3.
- **No production schema-per-tenant rollout.** The runbook documents the path; an operator must follow it under explicit P3.4 authorization.
- **No data migration.** No row export/import, no `db-per-tenant → schema-per-tenant` cutover. That is P3.4 / P3.5.
- **No automatic schema provisioning at runtime.** The P3.2 runtime intentionally errors loudly if a schema is missing; this remains the contract. Schema creation is an out-of-band operator action.
- **No P3.2 runtime change.** `database.py` is not edited.
- **No identity Alembic change.** `migrations/env.py` and `migrations_identity/env.py` are not edited. `migrations_identity/`'s 7-table allowlist remains as-is — note the deliberate distinction with `GLOBAL_TABLE_NAMES` in §5.3.

### 3.3 Why no tenant baseline revision in P3.3

P3.3 deliberately ships the migration plane (env + provisioning + runbook)
without an initial autogenerate revision. Reasons:

- **Reviewability.** A baseline revision captures the entire tenant table set
  in one large file (likely 500+ lines of `op.create_table(...)` calls). It
  benefits from its own dedicated review independent of the env wiring.
- **Plane vs. content.** Env wiring (where do migrations live, how are they
  configured) is conceptually separate from baseline content (which tables
  exist on day one). Coupling them in one PR forces reviewers to switch
  modes mid-diff.
- **Operator timing.** The operator team may want the baseline revision to
  land closer to the P3.4 cutover window so the captured table set reflects
  the cutover-time state, not a snapshot from weeks earlier.

The baseline revision lands as a separate sub-PR (suggested name:
**P3.3.3 — initial tenant baseline revision**) or is folded into P3.4
work, at the operator's discretion at the P3.4 stop-gate review (§9).

## 4. Settings (default off)

### 4.1 New `Settings` fields

P3.3.1 introduces two settings; both default to "disabled":

| Field | Default | Purpose |
| --- | --- | --- |
| `YUANTUS_ALEMBIC_TARGET_SCHEMA` | `""` (empty) | When non-empty, the tenant Alembic env runs against this schema. Empty means "tenant env is not configured for a target" and the env refuses to run. |
| `YUANTUS_ALEMBIC_CREATE_SCHEMA` | `false` | When `true`, the tenant Alembic env (or a separate provisioning helper) issues `CREATE SCHEMA IF NOT EXISTS "<schema>"` before running migrations. |

These settings are **only consulted by the tenant Alembic env and the
provisioning helper**. They are never read by `get_db()` / `get_db_session()`
or any runtime request path.

### 4.2 Why two settings, not one

`target_schema` is a *scope* selector. `create_schema` is an *action* flag.
Coupling them ("if target_schema is set, always create") would silently issue
DDL during a downgrade or a `--sql` dry-run. Splitting them lets the operator
pick: "create on the first upgrade, never thereafter".

## 5. Tenant Alembic Env (P3.3.1)

### 5.1 Location and shape

```
migrations_tenant/
  env.py
  script.py.mako
  versions/
alembic_tenant.ini
```

The structure mirrors `migrations_identity/`. `versions/` starts empty in
P3.3.1 (no actual migration scripts yet — those land per application table
groups in P3.3.2.x or later, and are out of scope for the bounded P3.3 PR).

### 5.2 Why a separate env (overriding P3.1 §5 Option 1)

P3.1 §5 named "Option 1 — tenant metadata filter in the main env" as the
"preferred first implementation; minimal runtime disruption". P3.3 deliberately
chooses Option 2 instead. Reasons specific to the merged code state:

1. **`migrations/env.py` *imports* identity models.** Filtering them out
   post-import is intrusive and risks accidental re-entry under
   autogenerate. Not importing them in a separate env is the cleaner
   isolation boundary.
2. **`migrations_identity/` precedent.** The codebase already has the
   "separate env per plane" pattern. Adding `migrations_tenant/` as the
   third sibling is reviewable and symmetric with the proven identity env.
3. **Independent revision sequences.** Each env owns its own
   `alembic_version` lineage. Mixing tenant migrations into the main
   env's revision history would create cross-plane confusion when an
   operator is debugging which migrations apply to which schema.
4. **Bootstrap cost is bounded.** `migrations_identity/env.py` is 120
   lines. The tenant env will be similar. The "larger bootstrap"
   concern in P3.1 §5 was overestimated relative to the precedent.

### 5.3 `target_metadata` — explicit `GLOBAL_TABLE_NAMES` exclusion

The tenant env's `target_metadata` is the combined `Base.metadata` +
`WorkflowBase.metadata` **minus an explicit allowlist of global tables**.
This list is **broader** than `migrations_identity/env.py`'s
`IDENTITY_TABLE_NAMES` because the codebase (verified via
`grep "__tablename__" src/yuantus/security src/yuantus/models`) carries
control-plane tables in three groups:

| Group | Tables | Source |
| --- | --- | --- |
| Identity (7) | `auth_tenants`, `auth_organizations`, `auth_users`, `auth_credentials`, `auth_org_memberships`, `auth_tenant_quotas`, `audit_logs` | `src/yuantus/security/auth/models.py`, `src/yuantus/models/audit.py` |
| RBAC (4) | `rbac_resources`, `rbac_permissions`, `rbac_roles`, `rbac_users` | `src/yuantus/security/rbac/models.py` |
| Legacy users (1) | `users` | `src/yuantus/models/user.py` |

All 12 are control-plane / cross-tenant artefacts and **must not** be created
inside per-tenant schemas. P3.3.1 must therefore introduce, in
`migrations_tenant/env.py`:

```python
GLOBAL_TABLE_NAMES = frozenset({
    # Identity (also allowlisted by migrations_identity/env.py)
    "auth_tenants", "auth_organizations", "auth_users",
    "auth_credentials", "auth_org_memberships", "auth_tenant_quotas",
    "audit_logs",
    # RBAC
    "rbac_resources", "rbac_permissions", "rbac_roles", "rbac_users",
    # Legacy general users
    "users",
})

tenant_metadata = MetaData()
for source in (Base.metadata, WorkflowBase.metadata):
    for name, table in source.tables.items():
        if name not in GLOBAL_TABLE_NAMES:
            table.tometadata(tenant_metadata)
target_metadata = tenant_metadata
```

**Naming rationale.** The constant is `GLOBAL_TABLE_NAMES` (not
`IDENTITY_TABLE_NAMES`) so the broader scope is visible at the call site.
`migrations_identity/env.py`'s `IDENTITY_TABLE_NAMES` (7 entries) is left
unchanged in P3.3 — it's an *allowlist for what the identity DB migrates*,
which is a different question from "what should be excluded from tenant
schemas". The two sets overlap on the 7 identity tables but diverge on
RBAC / legacy users (those tables are migrated by the main
`migrations/env.py` against the global DB, not by `migrations_identity/`).

### 5.3.1 Mandatory contract: exhaustive partition

P3.3.1 must add a contract test that asserts:

```python
combined = set(Base.metadata.tables) | set(WorkflowBase.metadata.tables)
tenant_set = set(tenant_metadata.tables)
assert combined == GLOBAL_TABLE_NAMES | tenant_set
assert GLOBAL_TABLE_NAMES.isdisjoint(tenant_set)
```

This guards two failure modes:
1. **A new global table** (e.g., a future `audit_*` or RBAC extension) gets
   created and the dev forgets to add it to `GLOBAL_TABLE_NAMES`. The
   exhaustive-partition test catches the orphan and forces an explicit
   classification decision.
2. **A new tenant table** that someone mistakenly named with an
   identity-looking prefix gets pulled into the global set. Same test
   catches the drift.

The test must run on the same imported metadata that the env produces —
i.e., after `import_all_models()` so all tables are registered. A leaner
"identity drift only" check (the original P3.1 §5 idea) is **insufficient**
because it does not cover RBAC or legacy users.

### 5.4 `version_table_schema` — load-bearing

Each tenant schema owns its own `alembic_version` table. The env's
`context.configure(...)` call must include:

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    version_table_schema=target_schema,
    include_schemas=True,
)
```

**Forbidden alternative:** a single global `alembic_version` for all tenants.
Reasons:

- Tenants drift in schema head over time during phased rollouts; a global
  table cannot represent multiple heads.
- A single global table is itself a cross-tenant write target — exactly the
  isolation boundary P3 is intended to establish.
- `alembic stamp` and `alembic downgrade` must operate per-tenant; a global
  table makes per-tenant rollback unsafe.

P3.3.1 must add a contract test that asserts `version_table_schema` is set to
the configured `target_schema` (not unset, not `"public"`).

### 5.5 Postgres-only guard

The tenant env must refuse to run against a non-Postgres URL — the same
discipline `_require_postgres_for_schema_mode()` enforces at runtime:

```python
url = get_database_url()
if not (url.startswith("postgresql") or url.startswith("postgres")):
    raise RuntimeError(
        "migrations_tenant/env.py requires a PostgreSQL DATABASE_URL. "
        "Got non-Postgres URL; refusing to run tenant migrations."
    )
```

This is enforced at env load, before any DDL is emitted. SQLite cannot
represent multiple schemas in the Postgres sense; running tenant migrations
against SQLite would be silently meaningless.

### 5.6 `target_schema` source

The tenant env reads the target schema from, in priority order:

1. Alembic `-x target_schema=<x>` command-line argument
   (`context.get_x_argument(as_dictionary=True)`).
2. `YUANTUS_ALEMBIC_TARGET_SCHEMA` environment variable.
3. Otherwise: refuse to run with a clear error.

Validation:

- The value must match the regex emitted by `tenant_id_to_schema()` —
  `^yt_t_[a-z0-9_]+$`, length ≤ 63.
- The env must reject any other shape, including an unprefixed name like
  `acme` or a name with quotes/whitespace.
- The validation function is shared with the provisioning helper (P3.3.2)
  to ensure both follow the same rule.

### 5.7 Online vs offline

**Online (`alembic upgrade`):**

```python
connectable = engine_from_config(
    configuration,
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
)
with connectable.connect() as connection:
    if create_schema:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}"'))
    connection.execute(text(f'SET search_path TO "{target_schema}", public'))
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=target_schema,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()
```

`SET search_path` here (not `SET LOCAL`) is acceptable because the connection
is dedicated to this migration run and is closed afterward — no pool reuse.

**Offline (`alembic upgrade --sql`):**

The emitted SQL **must begin with**
`SET search_path TO "<target_schema>", public;` so every subsequent DDL
statement is implicitly scoped to the target tenant schema. The env achieves
this by prepending the `SET search_path` line to the offline output and
using `version_table_schema=target_schema` so the `alembic_version` reference
also lands in the tenant schema.

This is the contract the env enforces and the test asserts. The taskbook
deliberately does **not** require every individual `CREATE` / `ALTER` /
`CREATE INDEX` statement to be schema-qualified (e.g., `"yt_t_acme"."items"`)
— that would require custom autogenerate render hooks beyond P3.3 scope. The
combination of leading `SET search_path` + `version_table_schema` provides
equivalent isolation for every Alembic-emitted statement that runs after the
SET line.

P3.3.1 must add a test that:
1. Runs `--sql` mode against the env with a configured `target_schema`.
2. Asserts the **first non-comment, non-blank line** of output is
   `SET search_path TO "<target_schema>", public;` (or equivalent quoting).
3. Asserts no DDL precedes that line.

**Mandatory operator review of `--sql` output**: the runbook must require
operators to read the emitted SQL before pasting into production. The env
**does not auto-execute** offline output. Operators must reject any output
that does not begin with `SET search_path` or that contains DDL above the
SET line (those would silently rely on the operator's ambient
`search_path`).

## 6. Schema Provisioning (P3.3.2)

### 6.1 Helper API

A bounded function in a new module (suggested location: `src/yuantus/scripts/tenant_schema.py`):

```python
def provision_tenant_schema(tenant_id: str, *, create: bool = True) -> str:
    """Resolve tenant_id → schema, then optionally CREATE SCHEMA IF NOT EXISTS.

    Returns the resolved schema name. Postgres-only. Idempotent for create=True.
    Does not change role/grant. Does not run migrations.
    """
```

Behavior:

- Calls `tenant_id_to_schema(tenant_id)` for the schema name.
- Calls `_require_postgres_for_schema_mode(settings)` for the URL guard.
- When `create=True`: opens a short-lived connection (NullPool), executes
  `CREATE SCHEMA IF NOT EXISTS "<schema>"`, commits, closes.
- When `create=False`: returns the resolved schema name without DDL (useful
  for "what schema would I create?" inspection).

### 6.2 What the helper does NOT do

- No `DROP SCHEMA`. (Destructive; P3.4 territory; out of scope for P3.3.)
- No `GRANT` / `REVOKE`. (Permissions decision below in §6.4.)
- No data import/export.
- No Alembic invocation. (Migrations are a separate operator step per §7.)

### 6.3 CLI surface (optional, bounded)

If the runbook benefits from a CLI, P3.3.2 may add:

```
python -m yuantus.scripts.tenant_schema create --tenant-id=<id>
python -m yuantus.scripts.tenant_schema resolve --tenant-id=<id>   # dry-run, prints schema name
```

Decide based on operator ergonomics; no CLI is required if the helper is
called from `python -c` in the runbook examples.

### 6.4 Schema ownership and permissions (bounded decision)

**Default in P3.3:** schemas are created by the role owning `DATABASE_URL`.
No `GRANT` / `REVOKE` / `OWNER TO` calls. Per-tenant role isolation is
explicitly **out of scope** for P3.3 and deferred to a later phase
(P3.5+ tenant role separation).

This decision is made now to prevent P3.3.2 from sprawling into RBAC. If the
operator needs separate roles per tenant, that requires a separate per-phase
opt-in.

## 7. Migration Safety, Rollback, Dry-Run (P3.3.2 runbook)

### 7.1 Production-safe sequence (per tenant)

The runbook (`docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`, deliverable of
P3.3.2) documents this as the only authorized sequence:

1. **Identify the tenant.** Confirm the tenant id is in the operator's
   approved list.
2. **Resolve schema name.** Run `python -m yuantus.scripts.tenant_schema
   resolve --tenant-id=<id>` and confirm the output matches the operator's
   expected `yt_t_<sanitized>` name.
3. **Provision schema.** Run `python -m yuantus.scripts.tenant_schema
   create --tenant-id=<id>`.
4. **Dry-run migrations.** Run `alembic -c alembic_tenant.ini
   -x target_schema=<schema> upgrade head --sql > tenant_<schema>.sql`.
5. **Operator reviews `tenant_<schema>.sql`.** Mandatory. The runbook
   includes a checklist.
6. **Apply migrations.** Run `alembic -c alembic_tenant.ini
   -x target_schema=<schema> upgrade head`. With `migrations_tenant/versions/`
   empty in the bounded P3.3 scope (§3.3), this is a wiring exercise — the
   env validates target schema, applies `SET search_path`, and exits with no
   DDL emitted. After a tenant baseline revision sub-PR ships, this step
   produces actual `CREATE TABLE` statements; until then, the runbook
   step is a no-op end-to-end check of env wiring.
7. **Wiring smoke.** Run a read-only query confirming the target schema
   exists in `pg_namespace`. **Do not** assert "application tables exist"
   — that is only true after a tenant baseline revision sub-PR lands.
   Until then the smoke succeeds when the schema exists and step 6
   produced no error.
8. **Leave runtime mode unchanged.** P3.3 does not enable
   `TENANCY_MODE=schema-per-tenant` for this tenant. P3.4 handles cutover.

### 7.2 Rollback

Per-schema rollback only. Cross-schema rollback is forbidden.

```
alembic -c alembic_tenant.ini -x target_schema=<schema> downgrade <revision>
```

Runbook must record:

- The exact revision id being rolled back to.
- A pre-rollback `alembic_version` snapshot for the schema.
- A post-rollback smoke that asserts the schema's `alembic_version`
  matches the expected target.

The runbook explicitly forbids running `downgrade` without an explicit
`-x target_schema` argument — the env must refuse, but the runbook also
forbids it as a defense in depth.

### 7.3 Dry-run discipline

Every production-bound migration starts as offline `--sql` output. The
runbook pins:

- The output filename pattern: `tenant_<schema>_<timestamp>.sql`.
- A minimum of one named reviewer signing off on the SQL diff.
- The reviewer checklist:
  - The **first non-comment, non-blank line** is
    `SET search_path TO "<target_schema>", public;`.
  - **No DDL** appears above that line.
  - All `CREATE TABLE` / `ALTER TABLE` / `CREATE INDEX` statements
    appear **after** the SET line (so they implicitly resolve into
    `<target_schema>`).
  - References to `alembic_version` resolve into `<target_schema>` (via
    the `version_table_schema` configuration), not `public`.
  - **No identity-table DDL** (`auth_*`, `audit_logs`), no RBAC-table DDL
    (`rbac_*`), and no legacy-`users`-table DDL appear anywhere.
- The reviewer signs in the runbook log; the SQL file is archived.

Offline output that does not begin with `SET search_path`, or that contains
DDL above the SET line, or that contains any global-table DDL, is rejected
by the review checklist.

## 8. P3.3 Sub-PR Breakdown

P3.3 ships in two sub-PRs (smaller than P3.2's three because the
provisioning helper is small and naturally bundles with the runbook):

### 8.1 P3.3.1 — Tenant Alembic env

Files:

- `migrations_tenant/env.py` (new, ~150 lines, modeled on
  `migrations_identity/env.py`).
- `migrations_tenant/script.py.mako` (new, copy of identity).
- `migrations_tenant/versions/` (new, empty `.gitkeep`).
- `alembic_tenant.ini` (new, ~30 lines).
- `src/yuantus/config/settings.py` (+2 fields, default off).
- `src/yuantus/scripts/tenant_schema.py` (new — `_validate_target_schema()`
  helper shared with the provisioning helper of P3.3.2).
- `src/yuantus/tests/test_tenant_alembic_env.py` (new):
  - `GLOBAL_TABLE_NAMES` contains exactly the 12 enumerated tables from
    §5.3 (7 identity + 4 RBAC + 1 legacy users).
  - `target_metadata` excludes every name in `GLOBAL_TABLE_NAMES`.
  - **Exhaustive partition** (§5.3.1):
    `combined == GLOBAL_TABLE_NAMES | tenant_set` and the two are disjoint.
    No orphans in either direction.
  - Env raises `RuntimeError` for non-Postgres URL.
  - Env raises clear error when `target_schema` is missing or fails the
    `^yt_t_[a-z0-9_]+$` regex.
  - `--sql` output's first non-comment, non-blank line is
    `SET search_path TO "<target_schema>", public;` and no DDL precedes it.
  - `version_table_schema` is set to `target_schema` in
    `context.configure(...)` (asserted via configuration introspection,
    not a real upgrade).
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_ALEMBIC_ENV_20260427.md` (new).
- `docs/DELIVERY_DOC_INDEX.md` (+1).

P3.3.1 acceptance:

- All tests pass.
- `migrations_tenant/versions/` is **empty by design** (§3.3); no tenant
  baseline revision generated. The first revision lands as a separate
  sub-PR or in P3.4.
- `migrations/env.py` and `migrations_identity/env.py` are unchanged.
  `IDENTITY_TABLE_NAMES` in the identity env stays at 7 entries (the
  identity DB's allowlist), independent of the new `GLOBAL_TABLE_NAMES`
  in the tenant env.
- `database.py` is unchanged (no P3.2 runtime change).
- Default settings keep `schema-per-tenant` migration plane disabled
  (`YUANTUS_ALEMBIC_TARGET_SCHEMA=""`,
  `YUANTUS_ALEMBIC_CREATE_SCHEMA=false`).

### 8.2 P3.3.2 — Provisioning helper + runbook

Files:

- `src/yuantus/scripts/tenant_schema.py` (extended with
  `provision_tenant_schema()` + optional CLI shim).
- `src/yuantus/tests/test_tenant_schema_provision.py` (new):
  - Resolver delegates to `tenant_id_to_schema()`.
  - Postgres-only guard (skip without `YUANTUS_TEST_PG_DSN`; non-Postgres
    URL raises clear error).
  - Idempotent `CREATE SCHEMA IF NOT EXISTS` (skip-without-DSN).
  - `create=False` mode returns name without DDL.
  - No `DROP SCHEMA`, no `GRANT` (assert via static check that the helper
    does not contain those tokens).
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md` (new — operational sequence,
  rollback, dry-run review checklist).
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_PROVISIONING_RUNBOOK_20260427.md`
  (new).
- `docs/DELIVERY_DOC_INDEX.md` (+2).

P3.3.2 acceptance:

- All tests pass.
- Helper is ≤ 80 lines.
- Runbook covers the full sequence from §7 above.
- No actual data migration step in the runbook.
- Default settings keep `YUANTUS_ALEMBIC_CREATE_SCHEMA=false`.

## 9. Hard P3.4 Stop Gate

Before P3.4 (data migration / cutover) starts, **all** of the following must
be in place. Lifted from P3.1 §9:

- [ ] A non-production Postgres target DSN provisioned and reachable.
- [ ] A named pilot tenant identified and approved.
- [ ] A backup/restore owner named.
- [ ] A migration rehearsal window scheduled.
- [ ] P3.3.1 + P3.3.2 merged and post-merge smoke green.
- [ ] A written table classification artifact: identity/global tables vs
      tenant application tables (this taskbook §5.3 supplies the seed; P3.4
      operator sign-off confirms current state).

If any item is missing, P3.4 must not begin. The runtime
`TENANCY_MODE=schema-per-tenant` must remain disabled.

## 10. Verification Plan

P3.3 taskbook (this PR) is documentation-only:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

P3.3.1 verification adds:

```bash
PYTHONPATH=src python3 -m pytest -q src/yuantus/tests/test_tenant_alembic_env.py
```

P3.3.2 verification adds:

```bash
PYTHONPATH=src python3 -m pytest -q src/yuantus/tests/test_tenant_schema_provision.py
```

## 11. Explicit Non-Goals

- No runtime code changes in this taskbook PR.
- No edits to `database.py`, `get_db()`, `get_db_session()`, or
  `tenant_id_to_schema()`.
- No edits to `migrations/env.py` or `migrations_identity/env.py`.
- No actual `CREATE SCHEMA` execution in this taskbook PR.
- No `DROP SCHEMA` anywhere in P3.3 (it is P3.4+ scope).
- No data movement in any P3.3 sub-PR.
- No `TENANCY_MODE=schema-per-tenant` enablement in any environment.
- No tenant role separation, GRANT/REVOKE, or RBAC work — deferred.
- No `cad_extractor` / observability / router-decomposition / shared-dev work.
