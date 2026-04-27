# DEV / Verification — Phase 3 P3.3.2 Tenant Provisioning Helper + Runbook (2026-04-27)

## 1. Goal

Implement P3.3.2 as a stacked follow-up to P3.3.1: add the bounded tenant schema provisioning helper/CLI and the operator runbook for schema provisioning and tenant Alembic wiring.

This PR remains default-off and does not enable schema-per-tenant runtime.

## 2. Files Changed

| File | Change |
| --- | --- |
| `src/yuantus/scripts/tenant_schema.py` | Adds `provision_tenant_schema()` plus `resolve` / `create` CLI commands. |
| `src/yuantus/tests/test_tenant_schema_provision.py` | Adds 7 contract tests, including one optional real-Postgres idempotency test skipped without `YUANTUS_TEST_PG_DSN`. |
| `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md` | New operator runbook for resolve → provision → offline SQL review → wiring upgrade → smoke. |
| `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_PROVISIONING_RUNBOOK_20260427.md` | This verification record. |
| `docs/DELIVERY_DOC_INDEX.md` | Adds the new DEV/verification MD and runbook entry. |
| `README.md` | Adds the new runbook to the `## Runbooks` section. |

## 3. Design Decisions

1. The helper delegates schema naming to `tenant_id_to_schema()` through `resolve_schema_for_tenant_id()`. There is still one schema-name source of truth.
2. `create=False` is a dry-run mode: it returns the managed schema name and never opens an engine.
3. Non-Postgres `DATABASE_URL` fails before `create_engine()` is called.
4. The create path uses a short-lived `NullPool` engine and disposes it after the operation.
5. The helper only issues `CREATE SCHEMA IF NOT EXISTS "<schema>"`. Privilege changes, ownership changes, role separation, and destructive cleanup are explicitly out of scope.
6. The runbook keeps P3.3.1’s wiring-only semantics: with empty tenant versions, no application tables are expected.

## 4. Verification

Provisioning helper contracts:

```bash
.venv/bin/python -m pytest -q src/yuantus/tests/test_tenant_schema_provision.py
```

Result:

```text
6 passed, 1 skipped
```

Compilation:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_schema.py \
  src/yuantus/tests/test_tenant_schema_provision.py
```

Result: passed.

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_schema_provision.py \
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
64 passed, 3 skipped, 1 warning
```

Runbook/doc-index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Result:

```text
5 passed
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

- `resolve` CLI prints the same schema as `tenant_id_to_schema()`.
- `create=False` does not open a DB engine.
- Non-Postgres URL raises before DB access.
- Create path uses idempotent schema creation and disposes the engine.
- Helper source has no privilege-changing commands.
- Runbook does not claim tenant application tables exist before a baseline revision.
- Runtime request path remains unchanged.

## 6. Explicit Non-Goals

- No tenant baseline migration revision.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No data migration or cutover.
- No tenant role separation or privilege management.
- No production database mutation in tests unless an operator explicitly supplies `YUANTUS_TEST_PG_DSN`.
