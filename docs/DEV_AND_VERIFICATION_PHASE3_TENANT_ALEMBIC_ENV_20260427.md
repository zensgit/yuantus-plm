# DEV / Verification — Phase 3 P3.3.1 Tenant Alembic Env (2026-04-27)

## 1. Goal

Implement P3.3.1 from `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_ALEMBIC_PROVISIONING_20260427.md`: add a default-off tenant Alembic environment that can validate a managed target schema, build tenant-only metadata, and emit offline SQL scoped by `SET search_path`.

This PR does not create tenant baseline migration revisions and does not run database DDL.

## 2. Files Changed

| File | Change |
| --- | --- |
| `alembic_tenant.ini` | New Alembic config pointing at `migrations_tenant/`, with logging config. |
| `migrations_tenant/env.py` | New Postgres-only tenant env. Reads `-x target_schema=` or `YUANTUS_ALEMBIC_TARGET_SCHEMA`, validates schema, sets `version_table_schema=target_schema`, prepends offline `SET search_path`, and optionally creates schema only when explicitly enabled. |
| `migrations_tenant/script.py.mako` | New revision template mirroring the existing migration template. |
| `migrations_tenant/versions/.gitkeep` | Keeps tenant versions directory empty by design. |
| `src/yuantus/config/settings.py` | Adds default-off `ALEMBIC_TARGET_SCHEMA` and `ALEMBIC_CREATE_SCHEMA`. |
| `src/yuantus/scripts/tenant_schema.py` | New shared helper for tenant metadata registration, global-table exclusion, schema validation, Postgres URL guard, and tenant-id schema preview. |
| `src/yuantus/tests/test_tenant_alembic_env.py` | New 19-case contract suite. |
| `docs/DELIVERY_DOC_INDEX.md` | Adds this verification MD. |

## 3. Design Decisions

1. `migrations_tenant/versions/` remains empty. P3.3.1 proves migration-plane wiring only; tenant baseline revision is P3.3.3 or P3.4.
2. `GLOBAL_TABLE_NAMES` has 15 entries, not the 12 listed in the P3.3 taskbook. Implementation audit found RBAC association tables: `rbac_user_roles`, `rbac_role_permissions`, `rbac_user_permissions`. Excluding only RBAC class tables would create dangling tenant-side join tables that reference missing global RBAC parents.
3. `audit_logs` is explicitly imported for exhaustive partition testing. The main env’s current import sequence does not always register it, but identity env treats it as control-plane.
4. Offline SQL uses the taskbook’s chosen contract: first non-comment, non-blank line is `SET search_path TO "<schema>", public;`; `version_table_schema` keeps `alembic_version` inside the tenant schema.
5. Online migrations configure Alembic first, then execute optional `CREATE SCHEMA` and `SET search_path` inside `context.begin_transaction()`. This avoids starting an implicit SQLAlchemy transaction before Alembic owns the migration transaction.
6. Runtime database routing remains untouched. `database.py`, `get_db()`, `get_db_session()`, and P3.2 behavior are unchanged.

## 4. Verification

Tenant Alembic contract suite:

```bash
.venv/bin/python -m pytest -q src/yuantus/tests/test_tenant_alembic_env.py
```

Result:

```text
19 passed, 1 warning
```

Compilation:

```bash
python3 -m py_compile \
  src/yuantus/scripts/tenant_schema.py \
  migrations_tenant/env.py \
  src/yuantus/tests/test_tenant_alembic_env.py
```

Result: passed.

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_alembic_env.py \
  src/yuantus/tests/test_database_tenancy.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
58 passed, 2 skipped, 1 warning
```

Boot check:

```bash
PYTHONPATH=src .venv/bin/python -c "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"
```

Result:

```text
routes=672 middleware=4
```

## 5. Review Checklist

- `GLOBAL_TABLE_NAMES` contains all identity/auth/audit/RBAC/legacy-user control-plane tables, including RBAC association tables.
- Tenant metadata is an exhaustive disjoint partition: `combined == GLOBAL_TABLE_NAMES | tenant_set`.
- Tenant env refuses non-Postgres database URLs.
- Missing or invalid target schema fails before migration execution.
- Offline `--sql` starts with `SET search_path` and no DDL precedes it.
- `version_table_schema=target_schema` is present for tenant `alembic_version`.
- No tenant baseline revision is introduced.
- No runtime request path is changed.

## 6. Explicit Non-Goals

- No tenant baseline migration revision.
- No schema provisioning helper/CLI implementation beyond shared validation helpers.
- No `CREATE SCHEMA` execution in tests.
- No data migration or cutover.
- No tenant role separation, `GRANT`, `REVOKE`, or `OWNER TO`.
- No production enablement of `TENANCY_MODE=schema-per-tenant`.
