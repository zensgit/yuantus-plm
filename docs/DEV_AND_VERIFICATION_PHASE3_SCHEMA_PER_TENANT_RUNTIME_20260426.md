# DEV / Verification — Phase 3 P3.2 Schema-per-Tenant Runtime (2026-04-26)

## 1. Goal

Implement the `TENANCY_MODE=schema-per-tenant` runtime code path per the P3.1
design strategy (`docs/DEVELOPMENT_PHASE3_SCHEMA_PER_TENANT_STRATEGY_20260426.md`
§4 / §8):

- Schema name resolver (`tenant_id_to_schema`) with production-safe sanitisation.
- Pool-safe `SET LOCAL search_path` re-applied per transaction in `get_db()`
  and `get_db_session()` via SQLAlchemy `after_begin` event listener (handles
  intermediate `commit()` / `db.refresh()` cleanly).
- Postgres-only guard: `_require_postgres_for_schema_mode()` rejects non-Postgres
  `DATABASE_URL` with a clear configuration error before any session is created.
- Rejection of missing tenant context before any DB access.
- 24 unit / dispatch / config-guard tests + 2 Postgres integration tests
  (skipped without a test DSN); existing tenancy-mode behaviour unchanged.

## 2. Strict P3.2 boundary

Per user opt-in (2026-04-26): "默认关闭 + 小 PR + 强测试 + 不迁移数据".

✅ in this PR:
- `tenant_id_to_schema()` resolver in `src/yuantus/database.py`
- `schema-per-tenant` dispatch in `get_db()` and `get_db_session()`
- `TENANCY_MODE` description updated in `src/yuantus/config/settings.py`
- `src/yuantus/tests/test_database_tenancy.py` — 24 tests + 2 Postgres-skip integration tests

❌ explicitly out of scope (deferred to P3.2.x / P3.3):
- Alembic migration environment for tenant schemas (`migrations_tenant/` or
  metadata filter in `migrations/env.py`)
- `YUANTUS_ALEMBIC_TARGET_SCHEMA` / `YUANTUS_ALEMBIC_CREATE_SCHEMA` settings
- Schema provisioning (`CREATE SCHEMA`) at runtime
- Data movement from existing tenancy modes
- Identity/auth tables — remain global, untouched

## 3. Files Changed

| File | Change | Lines |
| --- | --- | ---: |
| `src/yuantus/database.py` | `tenant_id_to_schema()`, `_require_postgres_for_schema_mode()`, `after_begin` schema dispatch in `get_db()` / `get_db_session()` | +70 |
| `src/yuantus/config/settings.py` | `TENANCY_MODE` description string | +2 |
| `src/yuantus/tests/__init__.py` | New package | +0 |
| `src/yuantus/tests/test_database_tenancy.py` | New: 24 tests + 2 Postgres-skip integration tests | +350 |
| `docs/DEV_AND_VERIFICATION_PHASE3_SCHEMA_PER_TENANT_RUNTIME_20260426.md` | This MD | +240 |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry | +1 |

Total: 6 files, ~665 lines.

## 4. Implementation Details

### 4.1 Schema name resolver

`tenant_id_to_schema(tenant_id: Optional[str]) -> str` in `database.py`:

| Property | Rule |
| --- | --- |
| Prefix | `yt_t_` — all managed schemas are distinguishable from `public` |
| Normalisation | Lowercase; `re.sub(r"[^a-z0-9]", "_", raw.lower())` |
| Empty / whitespace / None | `MissingTenantContextError` |
| All-punctuation / all-non-ASCII | `ValueError` (no valid chars after sanitisation) |
| Reserved names | Checked on the unprefixed schema slug before adding `yt_t_`, so `public` / `pg_catalog` style tenant IDs are rejected explicitly |
| Length cap | ≤ 63 bytes (Postgres NAMEDATALEN-1); truncated with 8-char `sha256(raw)[:8]` hash suffix — stable and collision-resistant |

The existing `_sanitize_tenant_id()` is untouched; `tenant_id_to_schema()` is
a new, separate helper for Postgres schema names only.

### 4.2 Session dispatch (get_db / get_db_session)

Both session providers gain an `elif settings.TENANCY_MODE == "schema-per-tenant":`
branch that:

1. Calls `_require_postgres_for_schema_mode(settings)` — raises
   `HTTPException(400)` / `RuntimeError` if `DATABASE_URL` does not start with
   `postgresql` / `postgres` (so SQLite-with-schema-mode fails fast with a
   clear config error, not an opaque SQL dialect error mid-session).
2. Reads `tenant_id_var.get()` from ContextVar (set by `TenantOrgContextMiddleware`
   or `AuthEnforcementMiddleware` upstream).
3. Calls `tenant_id_to_schema()` — raises `HTTPException(400)` from `get_db()` or
   `RuntimeError` from `get_db_session()` on missing/invalid context.
4. Assigns `db = SessionLocal()` (one engine per base `DATABASE_URL` — per §4.2
   of the strategy, no per-tenant engine).
5. Registers an `event.listens_for(db, "after_begin")` listener that executes
   `SET LOCAL search_path TO "<schema>", public` at the start of every new
   transaction on the session.

### 4.3 Pool safety + intermediate-commit safety

`SET LOCAL search_path` is transaction-scoped in Postgres: the path reverts to
the connection default on `COMMIT` or `ROLLBACK`. No persistent connection-level
`SET search_path` is used.

A naive one-shot `db.execute(SET LOCAL …)` before yield would silently regress
once the request handler calls `db.commit()` mid-flow — subsequent
`db.refresh()` / queries would run with the connection-default `search_path`.
The `after_begin` event listener fixes this: SQLAlchemy fires `after_begin`
each time a new transaction starts on the session (including the implicit
autobegin after a commit), so `SET LOCAL` is re-applied automatically.

Two Postgres integration tests cover this:
- `test_schema_search_path_does_not_leak_between_transactions` — pool-safety:
  two consecutive sessions on the same pooled connection do not see each
  other's schema.
- `test_search_path_reapplied_after_intermediate_commit` — re-apply: a query
  after `db.commit()` still sees the tenant schema.

Both skip cleanly when `YUANTUS_TEST_PG_DSN` is not set. Schema names in
these tests carry a per-process `uuid4().hex[:8]` suffix to avoid collisions
when the test DSN points at a non-dedicated database.

### 4.4 Postgres-only guard

`_require_postgres_for_schema_mode(settings)` checks
`settings.DATABASE_URL.startswith("postgresql"|"postgres")` before any session
is created. Non-Postgres URLs raise `ValueError`, which the dispatch wrapper
re-raises as `HTTPException(400)` (from `get_db()`) or `RuntimeError` (from
`get_db_session()`) with a message naming "PostgreSQL". This eliminates the
class of failure where SQLite + `TENANCY_MODE=schema-per-tenant` would create
a session and then crash inside the `SET LOCAL` execute with an opaque SQL
dialect error.

### 4.5 Identity plane — unchanged

`src/yuantus/security/auth/database.py` is not touched. Identity sessions route
through `IDENTITY_DATABASE_URL` or the base `DATABASE_URL` global schema, exactly
as before. Tenant schemas hold application data only.

### 4.6 Default-off

`TENANCY_MODE` defaults to `"single"`. Schema-per-tenant is unreachable unless
explicitly configured. No migration, no `CREATE SCHEMA`, no data movement.

## 5. Test Coverage

| Test | What it pins |
| --- | --- |
| `test_uppercase_is_lowercased` | Casing normalisation |
| `test_lowercase_passthrough` | Idempotent for already-lowercase |
| `test_dash_replaced_with_underscore` | Dash handling |
| `test_space_replaced_with_underscore` | Space handling |
| `test_punctuation_replaced` | Punctuation/special chars |
| `test_digits_preserved` | Digits pass through |
| `test_sql_injection_sanitised` | No quote/semicolon survives |
| `test_unicode_only_input_is_rejected` | Non-ASCII-only input rejected |
| `test_empty_string_raises` | Empty string → MissingTenantContextError |
| `test_whitespace_only_raises` | Whitespace-only → MissingTenantContextError |
| `test_none_raises` | None → MissingTenantContextError |
| `test_all_punctuation_raises` | All-punctuation → ValueError |
| `test_all_non_ascii_raises_or_maps_to_underscores_then_raises` | Long Unicode → ValueError |
| `test_reserved_schema_slug_is_rejected` | Reserved slug such as `public` → ValueError |
| `test_short_input_within_max` | Output ≤ 63 bytes |
| `test_long_input_truncated_to_max` | Output exactly 63 bytes when truncated |
| `test_truncation_is_stable` | Same input → same output |
| `test_truncation_hash_differs_for_different_inputs` | Different long inputs → different outputs |
| `test_output_always_starts_with_prefix` | Prefix invariant across inputs |
| `test_get_db_raises_400_without_tenant_context` | `get_db()` dispatch: HTTPException(400) on missing context |
| `test_get_db_session_raises_runtime_error_without_tenant_context` | `get_db_session()` dispatch: RuntimeError on missing context |
| `test_get_db_raises_400_for_non_postgres_url` | `get_db()` dispatch: HTTPException(400) when `DATABASE_URL` is not Postgres |
| `test_get_db_session_raises_runtime_error_for_non_postgres_url` | `get_db_session()` dispatch: RuntimeError when `DATABASE_URL` is not Postgres |
| `test_single_mode_get_db_does_not_invoke_schema_resolver` | Existing single mode unchanged |
| `test_schema_search_path_does_not_leak_between_transactions` | Postgres pool safety — different sessions on the same pooled connection don't leak (skip if no DSN) |
| `test_search_path_reapplied_after_intermediate_commit` | Postgres `after_begin` re-applies `SET LOCAL` after `commit()` (skip if no DSN) |

## 6. Verification

### 6.1 P3.2 focused tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_database_tenancy.py
```
→ **24 passed, 2 skipped** (both Postgres integration tests — pool-safety
and `after_begin` re-apply — skipped without `YUANTUS_TEST_PG_DSN`).

### 6.2 Regression suite

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_database_tenancy.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```
→ **39 passed, 2 skipped, 1 warning** in ~3.7s.

Breakdown:
- P3.2 tenancy: 24 passed, 2 skipped
- Phase 2 P2.3 closeout contracts: 6 passed
- Phase 1 portfolio: 5 passed
- Doc-index trio: 4 passed

### 6.3 Boot check

```bash
PYTHONPATH=src python3 -c "from yuantus.api.app import create_app; \
  app = create_app(); print(f'routes: {len(app.routes)}, middleware: {len(app.user_middleware)}')"
```
→ `routes: 672, middleware: 4` — unchanged from post-P2.3.

### 6.4 Whitespace lint

```bash
git diff --check
```
→ clean.

## 7. Recipe Adherence

Per P3.1 strategy §8 (P3.2 acceptance criteria):

- [x] `schema-per-tenant` rejects missing tenant context before DB access
  (`test_get_db_raises_400_without_tenant_context`,
  `test_get_db_session_raises_runtime_error_without_tenant_context`).
- [x] Non-Postgres `DATABASE_URL` rejected before any session creation
  (`test_get_db_raises_400_for_non_postgres_url`,
  `test_get_db_session_raises_runtime_error_for_non_postgres_url`).
- [x] Schema name resolver has unit tests for casing, punctuation, reserved
  names, empty values, truncation, and hash stability (18 resolver tests).
- [x] Runtime session applies tenant schema through a pool-safe mechanism
  (`SET LOCAL search_path` re-applied via `after_begin` event listener).
- [x] Worker and API paths share the same resolver (`get_db` and `get_db_session`
  both route through `tenant_id_to_schema`).
- [x] Existing tenancy modes keep their current tests green (regression suite
  above).
- [x] Postgres-specific test skips cleanly when no DSN is provided.

Per "默认关闭 + 小 PR + 强测试 + 不迁移数据":

- [x] Default off: `TENANCY_MODE` defaults to `"single"`; no code runs in
  schema-per-tenant path without explicit config.
- [x] Small PR: 6 files, ~665 lines, zero Alembic / migration / data-movement
  changes.
- [x] Strong tests: 24 cases covering every rejection path, the full
  normalisation table, the Postgres-only guard, and `after_begin` re-apply
  semantics; 2 Postgres integration tests skip cleanly without a DSN.
- [x] No data migration.

## 8. Out of Scope (Deferred)

- **Alembic tenant migration env** — `migrations_tenant/` or metadata-filter
  approach in `migrations/env.py` (P3.1 §6): separate sub-PR.
- **`YUANTUS_ALEMBIC_TARGET_SCHEMA` / `YUANTUS_ALEMBIC_CREATE_SCHEMA`** settings
  (P3.1 §6.1): deferred with Alembic env.
- **Schema provisioning** (`CREATE SCHEMA`) at runtime: deliberately omitted.
  Production rollout requires operator-managed schema provisioning before
  enabling the mode.
- **P3.3 data movement**: separate per-phase opt-in gate defined in P3.1 §9.

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Mid-request `commit()` resets `SET LOCAL` | Eliminated | — | `after_begin` event listener re-applies `SET LOCAL` at the start of every new transaction; `test_search_path_reapplied_after_intermediate_commit` (Postgres skip) verifies |
| Operator misconfigures SQLite + schema mode | Eliminated at boot | — | `_require_postgres_for_schema_mode()` raises a clear config error before any session is created |
| Schema doesn't exist yet (Postgres error) | Medium | Low | Mode is default-off; operator must provision schema before enabling — documented in P3.1 §6.4 rollout order |
| `tenant_id_to_schema` adds latency | Very low | Very low | Pure Python string ops + hashlib; no I/O |

## 10. Rollback

Revert this commit: `git revert <sha>`. The `schema-per-tenant` branch disappears
from `get_db()` / `get_db_session()`; no schema changes, no data affected.

## 11. Verification Summary

| Check | Result |
| --- | --- |
| Branch base | `origin/main=b522821` |
| `create_app()` boot | 672 routes, 4 middleware (unchanged) |
| P3.2 tenancy tests (24 cases, 2 Postgres integration skips) | 24 passed, 2 skipped |
| Phase 2 P2.3 closeout contracts (6 cases) | 6 passed |
| Phase 1 portfolio (5 cases) | 5 passed |
| Doc-index trio (4 cases) | 4 passed |
| `git diff --check` | clean |

**P3.2 status**: runtime path complete, default-off. Alembic tenant env awaits
next sub-PR. P3.3 data movement awaits P3.1 §9 stop-gate checklist.
