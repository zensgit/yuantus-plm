# DEV / Verification — Phase 3 P3.3 Tenant Alembic + Provisioning Taskbook (2026-04-27)

## 1. Goal

Execute Phase 3 P3.3 taskbook authorization: design how `migrations_tenant/`,
schema provisioning, dry-run, and rollback should be shaped so P3.3.1 / P3.3.2
implementation slices can be reviewed against a fixed contract.

This PR is documentation-only. It prepares P3.3.1 and P3.3.2 but does not
implement them.

## 2. Files Changed

| File | Change |
| --- | --- |
| `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_ALEMBIC_PROVISIONING_20260427.md` | New P3.3 taskbook covering tenant Alembic env, provisioning helper, migration safety / rollback / dry-run, sub-PR breakdown, and P3.4 stop gate. |
| `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_ALEMBIC_PROVISIONING_TASKBOOK_20260427.md` | This verification record. |
| `docs/DELIVERY_DOC_INDEX.md` | Adds both new docs in alphabetical order. |

## 3. Evidence Read Before Writing

Branch base for facts: `origin/main = 80cc9dc` (post-P3.2 merge).

| File | Evidence used |
| --- | --- |
| `src/yuantus/database.py` | `tenant_id_to_schema()`, `_require_postgres_for_schema_mode()`, `after_begin` schema dispatch are merged and default-off; P3.3 reuses `tenant_id_to_schema()` as the single resolver. |
| `migrations/env.py` lines 33–41, 51–61 | Imports identity models (`AuthUser`, `Tenant`, …) and combines `Base.metadata` + `WorkflowBase.metadata`; running this env against a tenant schema would create identity tables there. |
| `migrations_identity/env.py` lines 65–80 | Allowlist-based pattern with `IDENTITY_TABLE_NAMES = {auth_tenants, auth_organizations, auth_users, auth_credentials, auth_org_memberships, auth_tenant_quotas, audit_logs}`; the proven precedent for a separate env. |
| `src/yuantus/meta_engine/bootstrap.py` `import_all_models()` line 33 | Imports `yuantus.security.auth.models`; identity tables are unavoidably registered when `import_all_models()` runs, so the tenant env must filter explicitly. |
| `src/yuantus/security/auth/database.py` | Identity sessions stay on global `IDENTITY_DATABASE_URL` / `DATABASE_URL`; identity plane untouched in P3.3. |
| `src/yuantus/config/settings.py` | `TENANCY_MODE` already documents `schema-per-tenant`; no Alembic-target settings exist yet — P3.3.1 introduces them default-off. |
| `docs/DEVELOPMENT_PHASE3_SCHEMA_PER_TENANT_STRATEGY_20260426.md` §5, §6, §9 | The P3.1 design baseline. P3.3 explicitly supersedes §5 Option 1 with Option 2 (separate env) and lifts §9's stop-gate checklist verbatim. |

## 4. Key Design Decisions Captured

1. **Separate `migrations_tenant/` env** (overrides P3.1 §5 Option 1).
   Reason: `migrations/env.py` *imports* identity models; not importing
   them in a separate env is cleaner than filtering post-import. Symmetry
   with the existing `migrations_identity/` env is a reviewable
   structural pattern.
2. **`target_metadata` is the inverse of identity allowlist.** Same
   `IDENTITY_TABLE_NAMES` set as `migrations_identity/env.py`; tenant env
   excludes them. A drift-detection contract test pins the two lists
   together.
3. **`version_table_schema=<target_schema>` is mandatory.** Each tenant
   schema owns its own `alembic_version` row. A single global
   `alembic_version` is explicitly forbidden — it cannot represent
   per-tenant heads and would itself become a cross-tenant write target.
4. **Postgres-only guard at env load.** The tenant env refuses to run
   against a non-Postgres URL, mirroring P3.2's runtime guard.
5. **Two settings, default off.** `YUANTUS_ALEMBIC_TARGET_SCHEMA=""` and
   `YUANTUS_ALEMBIC_CREATE_SCHEMA=false`. Decoupled because target is a
   *scope* selector and create is an *action* flag.
6. **Schema name validation shared.** The schema-name regex
   (`^yt_t_[a-z0-9_]+$`, ≤ 63 chars) is checked by both the env's
   `-x target_schema` parser and the provisioning helper, so the same
   names flow through both planes.
7. **Schema ownership stays with the `DATABASE_URL` role.** No GRANT /
   REVOKE / OWNER TO in P3.3. Per-tenant role separation is a separate
   future phase.
8. **Two sub-PRs, not three.** P3.3.1 (env) is substantive; P3.3.2
   (helper + runbook) bundles a small helper with operational docs. No
   third PR is needed.
9. **Dry-run discipline pinned.** `--sql` output must be schema-qualified
   and operator-reviewed before paste-into-prod; the env never
   auto-executes offline output.
10. **Hard P3.4 stop gate.** Six checklist items lifted from P3.1 §9 must
    all be satisfied before any data-migration work begins.

## 5. Strict Boundary

In scope:

- P3.3 taskbook MD.
- P3.3 DEV/verification record (this MD).
- Doc index registration.

Out of scope (each is an explicit non-goal in §11 of the taskbook):

- No `migrations_tenant/env.py` file.
- No `alembic_tenant.ini`.
- No `src/yuantus/scripts/tenant_schema.py`.
- No `Settings` field additions.
- No `database.py` edit.
- No `migrations/env.py` or `migrations_identity/env.py` edit.
- No DB DDL / DML.
- No `TENANCY_MODE=schema-per-tenant` enablement.
- No P3.3.1 / P3.3.2 / P3.4 / P3.5 implementation.
- No Phase 1 / Phase 2 changes.

## 6. Review Checklist

- The taskbook accurately reflects the post-P3.2 codebase (file paths and
  line numbers in §2 and §3 were verified).
- The taskbook explicitly calls out and justifies overriding P3.1 §5's
  Option 1 recommendation.
- `IDENTITY_TABLE_NAMES` drift-detection contract is named (§5.3 of the
  taskbook).
- `version_table_schema` correctness is named as a contract (§5.4).
- Postgres-only guard is named for the migration plane (§5.5).
- Default-off settings (`YUANTUS_ALEMBIC_TARGET_SCHEMA=""`,
  `YUANTUS_ALEMBIC_CREATE_SCHEMA=false`) are named (§4.1).
- P3.3.1 and P3.3.2 each have a bounded file list and acceptance criteria
  (§8.1, §8.2).
- P3.4 stop-gate checklist is present and matches P3.1 §9 (§9).
- Non-goals are exhaustive and exclude data movement, runtime change,
  identity Alembic change, and RBAC scope creep (§11).
- `DELIVERY_DOC_INDEX.md` keeps both new entries sorted.

## 7. Verification

### 7.1 Doc-index trio

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Expected after edits: **4 passed**.

### 7.2 Whitespace lint

```bash
git diff --check
```

Expected after edits: clean.

### 7.3 No runtime tests required

This PR introduces no runtime code, no Alembic env, no settings, and no
helper. Therefore no runtime test suite is run for this PR.

P3.3.1 will add `src/yuantus/tests/test_tenant_alembic_env.py`. P3.3.2 will
add `src/yuantus/tests/test_tenant_schema_provision.py`. Neither exists in
this PR.

## 8. Recommended Sub-PR Split

Per taskbook §8 — repeated here so the operator can plan the next step:

| Sub-PR | Scope | Substance |
| --- | --- | --- |
| **P3.3.1** | `migrations_tenant/env.py` + `script.py.mako` + empty `versions/` + `alembic_tenant.ini` + 2 settings + shared `_validate_target_schema()` + `test_tenant_alembic_env.py` (6 contracts) + DEV/verification MD | ~150 lines env, ~40 lines settings/helper, ~150 lines tests |
| **P3.3.2** | `provision_tenant_schema()` helper + optional CLI shim + `test_tenant_schema_provision.py` (5 contracts) + `RUNBOOK_TENANT_MIGRATIONS_*.md` + DEV/verification MD | ~80 lines helper, ~120 lines tests, ~200 lines runbook |

Each sub-PR ships with its own DEV/verification MD and doc-index entry.

## 9. Next Step After This PR

P3.3.1 requires explicit opt-in. If authorized, start a separate
implementation branch:

```text
feat/tenant-alembic-env-20260427
```

Do not start P3.3.1 automatically after this taskbook merges. Per the
per-phase opt-in discipline, "继续" / "按建议执行" referring to the
taskbook merge does not authorize P3.3.1.
