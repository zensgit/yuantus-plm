# DEV / Verification - Phase 3 P3.1 Schema-per-Tenant Strategy (2026-04-26)

## 1. Goal

Execute Phase 3 P3.1 from
`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` section 7:

> Design doc + alembic migration strategy MD: how schema-per-tenant maps to
> existing tables; how `db-per-tenant` migrates to `schema-per-tenant`; how
> alembic identifies the target schema; transactional concerns.

This PR is intentionally documentation-only. It prepares P3.2/P3.3 but does
not implement them.

## 2. Files Changed

| File | Change |
| --- | --- |
| `docs/DEVELOPMENT_PHASE3_SCHEMA_PER_TENANT_STRATEGY_20260426.md` | New P3.1 strategy/taskbook for schema-per-tenant runtime, Alembic, identity-plane, and migration sequencing. |
| `docs/DEV_AND_VERIFICATION_PHASE3_SCHEMA_PER_TENANT_STRATEGY_20260426.md` | This verification record. |
| `docs/DELIVERY_DOC_INDEX.md` | Adds both new docs in alphabetical order. |

## 3. Evidence Read Before Writing

| File | Evidence |
| --- | --- |
| `src/yuantus/config/settings.py` | `TENANCY_MODE` currently documents/supports `single`, `db-per-tenant`, and `db-per-tenant-org`; no `schema-per-tenant` setting exists. |
| `src/yuantus/database.py` | Runtime tenant routing currently resolves to a full DB URL, caches engines/sessionmakers by URL, and has SQLite filename derivation for dev tenancy. |
| `src/yuantus/context.py` | Tenant/org/user/request identity is stored in `ContextVar`s. |
| `src/yuantus/api/middleware/context.py` | Request headers populate tenant/org context and snapshot onto `request.state`, which P2.3 already pinned for logging correctness. |
| `migrations/env.py` | Main Alembic env combines `Base` and `WorkflowBase` and imports identity models, which is unsafe to run directly as a tenant-schema migration env without filtering. |
| `migrations_identity/env.py` | Identity-only migration env exists for auth/audit control-plane tables. |
| `src/yuantus/security/auth/database.py` | Identity sessions use `IDENTITY_DATABASE_URL` or base `DATABASE_URL`, not tenant context. |
| `docs/DEVELOPMENT_DESIGN.md` | Existing roadmap explicitly names future Postgres schema-per-tenant or independent DB isolation. |
| `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` | Phase 3 defines P3.1 through P3.5 and requires a formal stop/reassess gate before P3.3. |

## 4. Key Design Decisions Captured

1. `schema-per-tenant` is Postgres-only and must not affect default SQLite dev.
2. Tenant maps to schema; org remains an application-level dimension inside
   the tenant schema.
3. Runtime schema resolution needs a schema-aware scope object; URL-only
   routing is insufficient.
4. Connection-pool safety requires per-transaction schema application, with
   `SET LOCAL search_path` preferred over persistent `SET search_path`.
5. Identity/auth/audit control-plane tables stay global by default.
6. Main Alembic metadata must be filtered or split before tenant-schema
   migrations; the current main env imports identity models.
7. P3.3 data migration requires a named pilot tenant, Postgres DSN,
   backup/restore owner, and rehearsal window.

## 5. Strict Boundary

In scope:

- P3.1 strategy/taskbook.
- P3.1 DEV/verification record.
- Doc index registration.

Out of scope:

- No `TENANCY_MODE=schema-per-tenant` runtime implementation.
- No `settings.py`, `database.py`, middleware, or Alembic code edits.
- No migration scripts.
- No DB mutation.
- No P3.2/P3.3/P3.4/P3.5 implementation.
- No Phase 2 observability or Phase 1 shell cleanup changes.

## 6. Review Checklist

- The strategy accurately reflects current URL-based tenant routing.
- The strategy explicitly calls out the identity-table risk in the current
  main Alembic env.
- P3.2 has bounded implementation surfaces and non-goals.
- P3.3 has a hard stop gate before data movement.
- The doc does not imply schema-per-tenant is already supported.
- `DELIVERY_DOC_INDEX.md` keeps both new entries sorted and references
  existing files.

## 7. Verification

### 7.1 Doc-index trio

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed result after edits: **4 passed** in 0.02s.

### 7.2 Whitespace lint

```bash
git diff --check
```

Observed result after edits: clean.

## 8. Next Step After P3.1

P3.2 requires explicit opt-in. If authorized, start a separate implementation
branch:

```text
feat/tenancy-schema-per-tenant-impl-20260426
```

Do not start P3.2 automatically after P3.1. P3.2 is runtime code and must be
reviewed separately from this design-only slice.
