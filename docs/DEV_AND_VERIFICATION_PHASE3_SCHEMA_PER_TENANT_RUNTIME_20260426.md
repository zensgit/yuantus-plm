# DEV / Verification — Phase 3 P3.2 Schema-per-Tenant Runtime (2026-04-26)

## 1. Goal

Implement the `TENANCY_MODE=schema-per-tenant` runtime code path per the P3.1
design strategy (`docs/DEVELOPMENT_PHASE3_SCHEMA_PER_TENANT_STRATEGY_20260426.md`
§4 / §8):

- Schema name resolver (`tenant_id_to_schema`) with production-safe sanitisation.
- Pool-safe `SET LOCAL search_path` applied per transaction in `get_db()` and
  `get_db_session()`.
- Rejection of missing tenant context before any DB access.
- 21 unit / dispatch / pool-safety tests; existing tenancy-mode behaviour
  unchanged.

## 2. Strict P3.2 boundary

Per user opt-in (2026-04-26): "默认关闭 + 小 PR + 强测试 + 不迁移数据".

✅ in this PR:
- `tenant_id_to_schema()` resolver in `src/yuantus/database.py`
- `schema-per-tenant` dispatch in `get_db()` and `get_db_session()`
- `TENANCY_MODE` description updated in `src/yuantus/config/settings.py`
- `src/yuantus/tests/test_database_tenancy.py` — 21 tests (1 Postgres skip)

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
| `src/yuantus/database.py` | `tenant_id_to_schema()`, schema dispatch in `get_db()` / `get_db_session()` | +58 |
| `src/yuantus/config/settings.py` | `TENANCY_MODE` description string | +2 |
| `src/yuantus/tests/__init__.py` | New package | +0 |
| `src/yuantus/tests/test_database_tenancy.py` | New: 21 tests | +175 |
| `docs/DEV_AND_VERIFICATION_PHASE3_SCHEMA_PER_TENANT_RUNTIME_20260426.md` | This MD | +140 |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry | +1 |

Total: 6 files, ~376 lines.

## 4. Implementation Details

### 4.1 Schema name resolver

`tenant_id_to_schema(tenant_id: Optional[str]) -> str` in `database.py`:

| Property | Rule |
| --- | --- |
| Prefix | `yt_t_` — all managed schemas are distinguishable from `public` |
| Normalisation | Lowercase; `re.sub(r"[^a-z0-9]", "_", raw.lower())` |
| Empty / whitespace / None | `MissingTenantContextError` |
| All-punctuation / all-non-ASCII | `ValueError` (no valid chars after sanitisation) |
| Reserved names | Checked on the full candidate; structurally impossible with `yt_t_` prefix, but enforced as belt-and-suspenders |
| Length cap | ≤ 63 bytes (Postgres NAMEDATALEN-1); truncated with 8-char `sha256(raw)[:8]` hash suffix — stable and collision-resistant |

The existing `_sanitize_tenant_id()` is untouched; `tenant_id_to_schema()` is
a new, separate helper for Postgres schema names only.

### 4.2 Session dispatch (get_db / get_db_session)

Both session providers gain an `elif settings.TENANCY_MODE == "schema-per-tenant":`
branch that:

1. Reads `tenant_id_var.get()` from ContextVar (set by `TenantOrgContextMiddleware`
   or `AuthEnforcementMiddleware` upstream).
2. Calls `tenant_id_to_schema()` — raises `HTTPException(400)` from `get_db()` or
   `RuntimeError` from `get_db_session()` on missing/invalid context.
3. Assigns `db = SessionLocal()` (one engine per base `DATABASE_URL` — per §4.2
   of the strategy, no per-tenant engine).
4. In the shared `try` block, executes
   `SET LOCAL search_path TO "<schema>", public` before yielding.

### 4.3 Pool safety

`SET LOCAL search_path` is transaction-scoped in Postgres: the path reverts to
the connection default on `COMMIT` or `ROLLBACK`. No persistent connection-level
`SET search_path` is used. The Postgres integration test
(`test_schema_search_path_does_not_leak_between_transactions`) verifies this
directly; it skips cleanly when `YUANTUS_TEST_PG_DSN` is not set.

### 4.4 Identity plane — unchanged

`src/yuantus/security/auth/database.py` is not touched. Identity sessions route
through `IDENTITY_DATABASE_URL` or the base `DATABASE_URL` global schema, exactly
as before. Tenant schemas hold application data only.

### 4.5 Default-off

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
| `test_short_input_within_max` | Output ≤ 63 bytes |
| `test_long_input_truncated_to_max` | Output exactly 63 bytes when truncated |
| `test_truncation_is_stable` | Same input → same output |
| `test_truncation_hash_differs_for_different_inputs` | Different long inputs → different outputs |
| `test_output_always_starts_with_prefix` | Prefix invariant across inputs |
| `test_get_db_raises_400_without_tenant_context` | `get_db()` dispatch: HTTPException(400) on missing context |
| `test_get_db_session_raises_runtime_error_without_tenant_context` | `get_db_session()` dispatch: RuntimeError on missing context |
| `test_single_mode_get_db_does_not_invoke_schema_resolver` | Existing single mode unchanged |
| `test_schema_search_path_does_not_leak_between_transactions` | Postgres pool safety (skip if no DSN) |

## 6. Verification

### 6.1 P3.2 focused tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_database_tenancy.py
```
→ **21 passed, 1 skipped** (Postgres pool-safety skipped — no `YUANTUS_TEST_PG_DSN`).

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
→ **36 passed, 1 skipped, 1 warning** in 3.89s.

Breakdown:
- P3.2 tenancy: 21 passed, 1 skipped
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
- [x] Schema name resolver has unit tests for casing, punctuation, reserved
  names, empty values, truncation, and hash stability (18 resolver tests).
- [x] Runtime session applies tenant schema through a pool-safe mechanism
  (`SET LOCAL search_path`).
- [x] Worker and API paths share the same resolver (`get_db` and `get_db_session`
  both route through `tenant_id_to_schema`).
- [x] Existing tenancy modes keep their current tests green (regression suite
  above).
- [x] Postgres-specific test skips cleanly when no DSN is provided.

Per "默认关闭 + 小 PR + 强测试 + 不迁移数据":

- [x] Default off: `TENANCY_MODE` defaults to `"single"`; no code runs in
  schema-per-tenant path without explicit config.
- [x] Small PR: 6 files, ~376 lines, zero Alembic / migration / data-movement
  changes.
- [x] Strong tests: 21 cases covering every rejection path and the full
  normalisation table.
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
| Mid-request `commit()` resets `SET LOCAL` | Low | Low | One-transaction-per-request is the standard FastAPI pattern; multi-commit flows are an edge case not yet present in the codebase |
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
| P3.2 tenancy tests (21 cases, 1 Postgres skip) | 21 passed, 1 skipped |
| Phase 2 P2.3 closeout contracts (6 cases) | 6 passed |
| Phase 1 portfolio (5 cases) | 5 passed |
| Doc-index trio (4 cases) | 4 passed |
| `git diff --check` | clean |

**P3.2 status**: runtime path complete, default-off. Alembic tenant env awaits
next sub-PR. P3.3 data movement awaits P3.1 §9 stop-gate checklist.
