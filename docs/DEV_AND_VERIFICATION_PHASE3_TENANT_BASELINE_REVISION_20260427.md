# DEV / Verification — Phase 3 P3.3.3 Tenant Baseline Revision (2026-04-27)

## 1. Goal

Close the gap left by P3.3.1 (`migrations_tenant/versions/` empty) by
generating a deterministic initial baseline Alembic revision. After this
PR, `alembic -c alembic_tenant.ini -x target_schema=<schema> upgrade head`
applied to a provisioned tenant schema actually creates the tenant
application table set, with each tenant's `alembic_version` row pointing
at `t1_initial_tenant_baseline`.

Per the task brief
(`docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_BASELINE_REVISION_20260427.md`):
no data migration, no `TENANCY_MODE=schema-per-tenant` enablement, no
runtime change to `database.py` / `get_db()` / request routing, no
identity/RBAC/users/global table creation in the tenant baseline.

## 2. Files Changed

| File | Change | Lines |
| --- | --- | ---: |
| `scripts/generate_tenant_baseline.py` | New: deterministic dev tool that strips cross-schema FKs and renders the revision via Alembic's `produce_migrations` against the PostgreSQL dialect. | +172 |
| `migrations_tenant/versions/t1_initial_tenant_baseline.py` | New: committed baseline revision. ~95 tenant tables, ~140 indexes, generator-output. | +1820 |
| `src/yuantus/scripts/tenant_schema.py` | `register_tenant_model_metadata()` extended to import 7 model packages that `import_all_models()` historically misses (`box`, `cutted_parts`, `document_sync`, `locale`, `maintenance`, `quality`, `report_locale`). Required for deterministic generation and runtime/baseline parity — see §4.2. | +14 |
| `src/yuantus/tests/test_tenant_baseline_revision.py` | New: 7 contract tests + 1 Postgres integration (skip without DSN). | +212 |
| `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md` | Replaces "wiring-only" caveats with baseline-ready instructions; smoke now asserts representative tenant tables and `alembic_version`. | ±35 |
| `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_BASELINE_REVISION_20260427.md` | Pre-existing (operator-authored task brief, retained as-is). | n/a |
| `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_BASELINE_REVISION_20260427.md` | This MD. | +180 |
| `docs/DELIVERY_DOC_INDEX.md` | +2 entries. | +2 |

## 3. Generation Strategy

### 3.1 Pipeline

```
build_tenant_metadata()          # full tenant MetaData with cross-schema FKs
        │
        ▼
_strip_cross_schema_fks()        # mutate-in-place: drop FKs whose target ∈ GLOBAL_TABLE_NAMES
        │                        # preserves columns (created_by_id, owner_id, …)
        ▼
sorted_tables (FK-respecting)    # SQLAlchemy topological sort, now FK-clean
        │
        ▼
UpgradeOps + DowngradeOps        # explicit CreateTableOp / CreateIndexOp / DropIndexOp / DropTableOp
        │                        # built directly (no compare_metadata against SQLite)
        ▼
render_python_code(...)          # Alembic's official renderer, PostgreSQL dialect
        │
        ▼
revision file (~142KB, 1820 lines, deterministic byte-identical across runs)
```

### 3.2 Why direct UpgradeOps instead of `compare_metadata` against SQLite

`compare_metadata` against an empty SQLite would render SQLite-flavoured
types for any Postgres-specific column (`postgresql.JSONB`, `UUID`,
`ARRAY`). Building `CreateTableOp.from_table()` directly and configuring
the rendering `MigrationContext` with `postgresql.dialect()` keeps the
output dialect-explicit and deterministic.

### 3.3 Cross-schema FK stripping

59 cross-schema FK constraints were stripped from the tenant metadata
before rendering. All 59 target one of `rbac_users`, `rbac_roles`,
`users` (global identity-plane tables). The columns themselves remain on
the tenant tables — `meta_items.created_by_id`, `meta_app_registry.installed_by_id`,
etc. — but without an Alembic `ForeignKeyConstraint`. This is the
explicit guidance in the task brief §4: "Prefer preserving the column
without the cross-schema FK constraint unless a safe same-schema target
exists." There is no safe same-schema target in schema-per-tenant
deployments because the referenced rows live in the global identity
plane.

The generator records the stripped FK count (`59`) and asserts it
matches the cross-FK probe done at orientation time. A future regen run
with the same metadata produces the same count.

### 3.4 Determinism

Two layers of determinism are pinned:

1. `sorted_tables` order is stable: SQLAlchemy's topological sort returns
   FK-respecting order with ties broken by `Table.key` (table name +
   schema). For tables with no FK dependencies, name order is alphabetical.
2. Index ordering is forced via `sorted(table.indexes, key=lambda i: (i.name or "", tuple(c.name for c in i.columns)))`.

`scripts/generate_tenant_baseline.py --check` regenerates in memory and
exits non-zero if the committed file differs.
`test_committed_baseline_matches_generator_output` enforces the same
contract in CI.

### 3.5 The `register_tenant_model_metadata()` extension

`import_all_models()` in `yuantus.meta_engine.bootstrap` historically
omits 7 model packages — `box`, `cutted_parts`, `document_sync`,
`locale`, `maintenance`, `quality`, `report_locale`. These packages
contribute ~16 additional tenant tables (e.g.,
`meta_maintenance_categories`, `meta_box_layouts`,
`meta_cutted_parts_*`). The packages get imported transitively when
`create_app()` loads their routers.

Before this PR, `build_tenant_metadata()` returned a different table
set depending on whether `create_app()` had been imported earlier in
the Python process — making the baseline non-deterministic and
sensitive to test ordering. The fix is `register_tenant_model_metadata()`
explicitly importing these 7 packages, so the tenant Alembic env's
`target_metadata` matches what a fully-booted app sees regardless of
import order. This keeps:

- The runtime tenant Alembic env consistent with the baseline.
- Future autogenerate runs (e.g., for follow-on tenant table
  additions) free of false "DROP TABLE" diffs caused by missing
  imports.
- The baseline byte-identical across CI runs.

This is a P3.3.1-internal extension (the `tenant_schema.py` migration
plane), not a runtime change to `database.py` / `get_db()` / request
routing.

## 4. Strict Boundary

In scope:

- One static, committed baseline revision under
  `migrations_tenant/versions/`.
- Generator script (`scripts/generate_tenant_baseline.py`) — committed
  for reproducibility, never imported at runtime.
- Contract tests for the revision shape and content.
- Optional Postgres integration test, skipped without
  `YUANTUS_TEST_PG_DSN`.
- Runbook update from "wiring-only" language to baseline-ready
  instructions, including post-upgrade smoke and rollback.
- DEV/verification MD + doc index entries.

Out of scope:

- No data migration. The baseline only creates tables; it does not
  copy or transform any rows.
- No runtime change to `database.py`, `get_db()`, `get_db_session()`,
  or request routing.
- No `TENANCY_MODE=schema-per-tenant` enablement in any environment.
- No identity / RBAC / users / global table DDL in the tenant baseline.
  Those tables stay on the global identity plane and are migrated
  separately by `migrations/env.py` and `migrations_identity/env.py`.
- No `GRANT` / `REVOKE` / `OWNER TO` / `DROP SCHEMA` operations.
- No tenant role separation work.

## 5. Test Coverage

| Test | What it pins |
| --- | --- |
| `test_versions_dir_has_exactly_one_revision` | Only `t1_initial_tenant_baseline.py` exists — no orphan revisions. |
| `test_baseline_has_no_down_revision` | `revision = "t1_initial_tenant_baseline"`, `down_revision = None`. Baseline is the root of the tenant revision tree. |
| `test_revision_source_contains_no_global_table_identifiers` | Precise quoted-identifier scan: every `GLOBAL_TABLE_NAMES` entry is absent as `'name'` / `"name"` / FK target string. Substring matches inside benign tenant names like `meta_signature_audit_logs` are not flagged. |
| `test_revision_has_no_cross_schema_fk_constraints` | Parses every `sa.ForeignKeyConstraint(...)` call in the file and asserts no target table is in `GLOBAL_TABLE_NAMES`. |
| `test_generator_output_is_deterministic` | Two calls to `generate()` in the same process produce byte-identical output. |
| `test_committed_baseline_matches_generator_output` | The committed file equals what the generator produces *now* — drift detection if `register_tenant_model_metadata` or model definitions change. First-diff line is reported on failure. |
| `test_baseline_creates_representative_tenant_tables` | Spot check: `op.create_table('meta_items', …)`, `meta_files`, `meta_conversion_jobs`, `meta_relationships` are all in the upgrade body. Catches a regen that accidentally drops a major application table. |
| `test_baseline_upgrade_creates_tenant_tables_on_postgres` *(skip without `YUANTUS_TEST_PG_DSN`)* | End-to-end: provision a unique schema with a per-process uuid suffix, run `alembic upgrade head` via subprocess, assert representative tenant tables exist, no global tables present, `alembic_version` row equals `t1_initial_tenant_baseline`, drop schema CASCADE on cleanup. |

## 6. Verification

### 6.1 Generator self-check

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_tenant_baseline.py --check
```
→ `ok: committed revision matches generator output`.

### 6.2 P3.3.3 focused tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_baseline_revision.py
```
→ **7 passed, 1 skipped** in 0.49s.

### 6.3 Cross-suite regression (P3.3.1 + P3.3.2 + P3.3.3 + Phase 1/2 contracts)

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_baseline_revision.py \
  src/yuantus/tests/test_tenant_alembic_env.py \
  src/yuantus/tests/test_tenant_schema_provision.py \
  src/yuantus/tests/test_database_tenancy.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py
```
→ **67 passed, 4 skipped, 1 warning** in 4.29s.

Order-independence verified by running with `create_app()`-using tests
first:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/tests/test_database_tenancy.py \
  src/yuantus/tests/test_tenant_alembic_env.py \
  src/yuantus/tests/test_tenant_schema_provision.py \
  src/yuantus/tests/test_tenant_baseline_revision.py
```
→ **67 passed, 4 skipped, 1 warning** in 4.10s.

### 6.4 Doc-index trio

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```
→ **4 passed**.

### 6.5 Compile + boot

```bash
.venv/bin/python -m py_compile \
  scripts/generate_tenant_baseline.py \
  migrations_tenant/versions/t1_initial_tenant_baseline.py \
  src/yuantus/scripts/tenant_schema.py \
  src/yuantus/tests/test_tenant_baseline_revision.py

PYTHONPATH=src .venv/bin/python -c "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"
```
→ All compile cleanly. Boot: routes/middleware unchanged from
post-P3.3.2 main (P3.3.3 adds zero runtime routes / zero middleware).

### 6.6 Postgres integration (skip without DSN)

`YUANTUS_TEST_PG_DSN` was not set in this verification run. The Postgres
integration test is unblocked locally with:

```bash
YUANTUS_TEST_PG_DSN=postgresql+psycopg://yuantus:yuantus@localhost:5432/yuantus_p3_test \
  PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_baseline_revision.py::test_baseline_upgrade_creates_tenant_tables_on_postgres
```

Operator can run this on a non-production Postgres instance to verify
the end-to-end `provision → upgrade → smoke → drop` cycle.

### 6.7 Whitespace lint

```bash
git diff --check
```
→ clean.

## 7. Stop-Conditions Reviewed

The task brief §11 lists four stop conditions; all are satisfied:

| Stop condition | Status |
| --- | --- |
| Global/control-plane table DDL appears in tenant SQL | ✅ Not present (per `test_revision_source_contains_no_global_table_identifiers` and `test_revision_has_no_cross_schema_fk_constraints`). |
| Tenant table FKs require excluded global tables in the same schema | ✅ All 59 cross-schema FKs were stripped at generation time; columns preserved without FK constraint. |
| Alembic offline SQL does not begin with tenant `SET search_path` | ✅ Inherited from P3.3.1 env; the env still emits `SET search_path TO "<schema>", public;` first in offline mode. |
| The generated revision is non-deterministic between runs | ✅ Pinned by `test_generator_output_is_deterministic` and `test_committed_baseline_matches_generator_output`. Order-independent across test suites (verified §6.3). |

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Future model changes silently invalidate the baseline | Low | Medium | `test_committed_baseline_matches_generator_output` fails CI, telling the dev to re-run `python scripts/generate_tenant_baseline.py`. |
| New `meta_engine.*` model package added without adding to `register_tenant_model_metadata` | Medium | Medium | The same drift test catches this at PR time. The exhaustive partition contract (`test_tenant_metadata_excludes_global_tables_and_partitions_combined_metadata` from P3.3.1) catches additions to `Base.metadata` that aren't classified. |
| Postgres-specific type missing from generator imports | Low | Low | Generator inspects rendered output for `postgresql.*` references and conditionally adds the dialect import. Future types (e.g., `postgresql.ARRAY`) inherit the same conditional. |
| Operator runs `alembic downgrade base` without `-x target_schema` | Low | High | Tenant env's `_validate_target_schema` raises if missing; runbook §8 forbids it explicitly. |

## 9. P3.4 Stop Gate (unchanged from P3.3 taskbook §9)

P3.4 (data migration / runtime cutover) requires **all** of:

- [ ] A non-production Postgres target DSN provisioned.
- [ ] A named pilot tenant identified and approved.
- [ ] A backup/restore owner named.
- [ ] A migration rehearsal window scheduled.
- [ ] **P3.3.1 + P3.3.2 + P3.3.3** merged and post-merge smoke green.
- [ ] Written table classification artifact signed off.

If any item is missing, P3.4 must not begin.
`TENANCY_MODE=schema-per-tenant` must remain disabled.

## 10. Rollback

This PR is additive: a new revision file, a new generator, a new test
file, and doc updates. Revert with:

```
git revert <commit>
```

After revert, `migrations_tenant/versions/` returns to empty;
`alembic -c alembic_tenant.ini upgrade head` returns to wiring-only
behaviour from P3.3.2. No DB state to restore (this PR adds no schema
or data writes by itself; the operator runs migrations against tenant
schemas as a separate action).

## 11. Verification Summary

| Check | Result |
| --- | --- |
| Branch base | `origin/main = 0db8ede` (post-P3.3.2 merge) |
| Generator `--check` | ok |
| P3.3.3 focused tests (8 cases, 1 Postgres skip) | 7 passed, 1 skipped |
| Cross-suite (67 cases, 4 Postgres/Pool skips) | 67 passed, 4 skipped |
| Order-independent regression | passes both orderings |
| Doc-index trio | 4 passed |
| Compile (4 files) | clean |
| Boot | routes/middleware unchanged |
| `git diff --check` | clean |
