# Development Plan - Phase 3 P3.1 Schema-per-Tenant Strategy (2026-04-26)

## 1. Goal

Phase 3 targets production-grade Postgres tenancy isolation. P3.1 is the
design and migration-strategy slice only. It defines how a future
`TENANCY_MODE=schema-per-tenant` should map onto the current Yuantus runtime,
Alembic setup, and migration path without changing runtime behavior in this
PR.

This document is the taskbook for P3.2/P3.3. It intentionally does not add a
new settings value, database resolver code, Alembic code, migration scripts, or
tests.

## 2. Current Implementation Facts

Evidence from the current codebase:

| Area | Current behavior | Design implication |
| --- | --- | --- |
| Settings | `TENANCY_MODE` supports `single`, `db-per-tenant`, and `db-per-tenant-org` only (`src/yuantus/config/settings.py`). | `schema-per-tenant` is a new mode and must be guarded behind explicit settings docs/tests. |
| Request context | `TenantOrgContextMiddleware` loads `x-tenant-id` and `x-org-id` into `ContextVar`s and snapshots them onto `request.state`. | P3.2 must reuse the same tenant context source. No new request headers. |
| Runtime DB routing | `resolve_database_url()` returns a complete DB URL; per-tenant caches are keyed by URL. | Schema-per-tenant cannot be represented by URL alone. It needs an explicit tenant schema scope. |
| Existing isolation modes | `db-per-tenant` and `db-per-tenant-org` either use `DATABASE_URL_TEMPLATE` or derived SQLite filenames. | These modes remain untouched and provide the rollback fallback. |
| Main Alembic env | `migrations/env.py` combines `Base` and `WorkflowBase` and also imports identity/auth models. | Running the current env directly against tenant schemas would duplicate identity tables unless P3.2/P3.3 filters tenant metadata. |
| Identity Alembic env | `migrations_identity/env.py` already provides an identity-only migration environment for auth/audit tables. | Keep identity as a global control plane by default; tenant schemas hold application data only. |
| Identity runtime DB | `src/yuantus/security/auth/database.py` routes identity sessions through `IDENTITY_DATABASE_URL` or `DATABASE_URL`. | Schema-per-tenant must not route auth sessions through tenant schemas. |

## 3. Target Semantics

### 3.1 Supported mode

Add one future mode:

```text
YUANTUS_TENANCY_MODE=schema-per-tenant
```

This mode is Postgres-only. SQLite remains covered by `single`,
`db-per-tenant`, and `db-per-tenant-org`.

### 3.2 Tenant scope

P3 should implement tenant-level schemas, not tenant+org schemas:

```text
tenant_id -> Postgres schema
org_id    -> normal row-level/application dimension inside the tenant schema
```

Rationale:

- The existing `db-per-tenant-org` mode already covers the strongest
  tenant+org isolation case.
- Schema-per-org multiplies schema count and Alembic runtime by organization
  count, which increases operational risk without a current production trigger.
- Most current context and auth flows already model tenant as the top-level
  isolation boundary.

### 3.3 Schema naming

P3.2 should add a deterministic schema resolver with these properties:

| Requirement | Rule |
| --- | --- |
| Prefix | Use a fixed prefix, e.g. `yt_t_`, so managed tenant schemas are distinguishable from `public` and extension schemas. |
| Allowed chars | Lowercase ASCII letters, digits, and underscore only. |
| Empty/invalid input | Reject before DB access; do not silently map to `default` in schema mode. |
| Length | Cap at a safe identifier length and append a stable hash suffix when truncating. |
| Reserved schemas | Forbid `public`, `information_schema`, `pg_catalog`, `pg_toast`, and the identity schema name if one is introduced. |
| Quoting | Always quote identifiers through SQLAlchemy/dialect helpers; never string-concatenate untrusted tenant IDs into SQL. |

The existing `_sanitize_tenant_id()` helper is not sufficient for production
schema names because it preserves uppercase and dash characters and falls back
to `default` for empty values. P3.2 should add a new schema-specific helper
rather than repurposing the SQLite filename helper.

## 4. Runtime Strategy for P3.2

### 4.1 Database URL resolution

For `schema-per-tenant`, `DATABASE_URL` remains the base Postgres database URL.
`DATABASE_URL_TEMPLATE` is not used.

P3.2 should introduce an internal resolved scope object rather than overloading
the current URL-only routing:

```python
ResolvedDatabaseScope(
    database_url=settings.DATABASE_URL,
    schema_name="yt_t_acme",
    cache_key="postgresql://...|schema=yt_t_acme",
)
```

The public `resolve_database_url()` can stay compatible for existing callers,
but session creation needs schema awareness.

### 4.2 Engine and session cache

Use one SQLAlchemy engine per base Postgres URL. Do not create one engine per
tenant schema.

Recommended P3.2 shape:

- Engine cache key: base `DATABASE_URL`.
- Sessionmaker cache key: base `DATABASE_URL`.
- Tenant schema application: per session / per transaction, not per engine.

### 4.3 Search path safety

P3.2 must be connection-pool safe. Avoid persistent `SET search_path` that can
leak tenant scope across pooled connections.

Recommended contract:

1. Open a session.
2. Start the transaction before the first application query.
3. Execute `SET LOCAL search_path TO <tenant_schema>, public` using quoted
   identifiers.
4. Run application queries.
5. Commit/rollback closes the transaction and discards the local search path.

Any design that uses persistent `SET search_path` must include a connection
reset hook and a failing regression test proving tenant scope does not leak
after connection reuse. `SET LOCAL` is preferred.

### 4.4 Worker parity

Workers already rely on the same `ContextVar` model. P3.2 must keep this
contract:

- API request path: auth/context middleware sets tenant context.
- Worker path: CLI/job runner injects tenant context before opening DB
  sessions.
- Both paths call the same schema resolver and session creation code.

## 5. Identity Plane Decision

Default decision: identity/auth/audit control-plane tables stay global and are
not duplicated into every tenant schema.

Tenant schemas should hold application data tables. Identity data remains in:

- `IDENTITY_DATABASE_URL`, when configured; or
- the base `DATABASE_URL` global schema/control plane, when not configured.

P3.2/P3.3 must therefore avoid applying auth identity tables into tenant
schemas. This is the most important migration-env gap because
`migrations/env.py` currently imports identity models into its combined
metadata for monolithic deployments.

P3.2/P3.3 must introduce one of these bounded solutions:

| Option | Description | Recommendation |
| --- | --- | --- |
| Tenant metadata filter | Main tenant migration env filters out known identity tables before running per-tenant schema migrations. | Preferred first implementation; minimal runtime disruption. |
| Separate tenant migration env | Add `migrations_tenant/` for tenant application tables only. | Cleaner long-term but larger bootstrap. |
| Duplicate identity per tenant | Apply auth tables to every tenant schema. | Reject for P3. It breaks the global identity-plane model. |

## 6. Alembic Strategy for P3.2/P3.3

### 6.1 Main variables

Introduce explicit migration inputs, not implicit tenant context:

```text
YUANTUS_ALEMBIC_TARGET_SCHEMA=yt_t_acme
YUANTUS_ALEMBIC_CREATE_SCHEMA=true|false
```

The runtime request context should not be required for Alembic.

### 6.2 Online migration flow

For each tenant schema:

1. Connect to `DATABASE_URL` with `NullPool`.
2. Validate and quote `YUANTUS_ALEMBIC_TARGET_SCHEMA`.
3. Optionally `CREATE SCHEMA IF NOT EXISTS <schema>`.
4. Apply `SET search_path TO <schema>, public` for the migration connection.
5. Configure Alembic with tenant application metadata only.
6. Store the Alembic version table in the target schema.
7. Run migrations.
8. Run a post-upgrade smoke query inside the same schema.

### 6.3 Offline migration flow

Offline SQL generation is allowed only when a target schema is supplied. The
generated SQL must be labeled with the target schema and reviewed before use.
Do not generate a single generic SQL file that silently relies on an operator's
ambient `search_path`.

### 6.4 Migration order

Production rollout order:

1. Run identity/global migrations.
2. Provision each tenant schema.
3. Run tenant application migrations per schema.
4. Run tenant isolation smoke tests.
5. Enable `TENANCY_MODE=schema-per-tenant`.

Do not enable runtime schema-per-tenant before all target tenant schemas are at
the expected Alembic head.

## 7. Upgrade Path from Existing Modes

P3.3 handles data movement. P3.1/P3.2 do not.

Recommended P3.3 plan:

| Step | Action | Gate |
| --- | --- | --- |
| 1 | Freeze writes for the source tenant DB. | Operator confirmation. |
| 2 | Backup source SQLite/tenant DB and target Postgres DB. | Backup artifacts recorded. |
| 3 | Export source tables in FK-safe order. | Row counts captured. |
| 4 | Create target schema and run tenant migrations. | Schema at expected head. |
| 5 | Import rows with identity/global tables excluded. | Import logs retained. |
| 6 | Validate row counts and sampled relationship integrity. | Diff report green. |
| 7 | Run tenant isolation contract. | No cross-tenant visibility. |
| 8 | Switch runtime config for the pilot tenant. | Rollback window open. |

Rollback for P3.3 is config rollback to the previous mode plus restore from the
pre-migration backup if writes happened after cutover.

## 8. P3.2 Implementation Taskbook

P3.2 may touch:

- `src/yuantus/config/settings.py`
- `src/yuantus/database.py`
- `migrations/env.py` or a new tenant-specific migration helper/env
- focused tests under `src/yuantus/.../tests/`
- `docs/DELIVERY_DOC_INDEX.md`
- one DEV/verification MD

P3.2 must not:

- Move existing data.
- Change `single`, `db-per-tenant`, or `db-per-tenant-org` behavior.
- Route identity DB sessions through tenant schemas.
- Require Postgres for the default local dev path.
- Add tenant/user/job labels to Phase 2 Prometheus metrics.

P3.2 acceptance:

- `schema-per-tenant` rejects missing tenant context before DB access.
- Schema name resolver has unit tests for casing, punctuation, reserved names,
  empty values, truncation, and hash stability.
- Runtime session applies tenant schema through a pool-safe mechanism.
- Worker and API paths share the same resolver.
- Existing tenancy modes keep their current tests green.
- Postgres-specific integration tests skip cleanly when no Postgres test DSN is
  provided.

## 9. P3.3 Stop Gate

Before P3.3 starts, require all of the following:

- A non-production Postgres target DSN.
- A named pilot tenant.
- A backup/restore owner.
- A migration rehearsal window.
- P3.2 merged and post-merge smoke green.
- A written table classification: identity/global tables vs tenant
  application tables.

If any item is missing, do not begin P3.3. Keep `schema-per-tenant` disabled.

## 10. Verification Plan

P3.1 verification is documentation-only:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

P3.2 verification should add:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_database_tenancy.py \
  src/yuantus/api/tests/test_tenant_context_middleware.py
```

P3.3 verification should add a Postgres-backed rehearsal command, but only
after the pilot DSN exists.

## 11. Explicit Non-Goals

- No runtime code in P3.1.
- No Alembic code in P3.1.
- No migration script in P3.1.
- No database mutation.
- No production enablement.
- No deletion or rewrite of existing tenancy modes.
- No UI/admin endpoint.
- No scheduler, observability, router-decomposition, or 142 shared-dev work.
