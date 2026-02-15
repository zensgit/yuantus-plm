# Dev Log (2026-02-15): verify_all Stack Reuse + MT DB Resolution Hardening

## Context

Running:

```bash
RUN_DEDUP=1 START_DEDUP_STACK=1 USE_DOCKER_WORKER=1 bash scripts/verify_all.sh
```

hit two operational issues:

1. Port conflict during stack startup (`59000 already allocated`) when a healthy stack was already running in another compose project.
2. DB/env mismatch in `db-per-tenant-org` context:
   - placeholder `YUANTUS_DATABASE_URL=sqlite:///yuantus_mt_skip.db` could be picked up
   - identity DB name could be incorrectly derived as `yuantus_identity_mt_pg` even when runtime uses `yuantus_identity`.

Both issues caused false-negative regressions in scripts that seed/login users and query DB directly.

## Changes

1. `scripts/verify_all.sh`: reusable healthy stack detection

- Added:
  - `first_healthy_dedup_base_url()`
  - `has_running_compose_worker()`
  - `can_reuse_running_stack()`
- Behavior:
  - with `START_DEDUP_STACK=1`, preflight first checks whether API (+ dedup when enabled) is already healthy.
  - if healthy, skip compose startup and reuse existing services instead of failing on port conflicts.
  - when dedup endpoint is reused, propagate it to `YUANTUS_DEDUP_VISION_BASE_URL`.

2. `scripts/verify_all.sh`: MT placeholder DB protection

- Added:
  - `is_mt_skip_database_url()`
- Behavior:
  - ignores placeholder `sqlite:///...yuantus_mt_skip.db` for `DB_URL` derivation.
  - avoids deriving identity DB URL from placeholder DB URL.

3. `scripts/verify_all.sh`: runtime postgres/identity resolution from running API compose project

- Added:
  - `resolve_api_compose_project()`
  - `resolve_postgres_container_id_from_api_project()`
  - `resolve_postgres_port_line_from_api_project()`
  - `resolve_identity_db_name_for_runtime()`
- Behavior:
  - if static `docker compose ... -p yuantusplm port postgres` probing fails, fallback to the compose project that owns current API port.
  - identity DB name is inferred from actual postgres database list (`yuantus_identity` / `yuantus_identity_mt_pg`) instead of tenancy-only hardcoding.

4. `scripts/verify_version_files.sh`: identity-seeding collision reduction

- Added per-run viewer username:
  - `VIEWER_USER="viewer-$TS"`
- viewer seed/login now use `VIEWER_USER`.
- viewer seed explicitly uses `--no-superuser`.

5. CI contract tests

- Added:
  - `src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_stack_reuse_on_start_conflict.py`
  - `src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_mt_skip_db_placeholder.py`
  - `src/yuantus/meta_engine/tests/test_ci_contracts_version_file_binding_viewer_uniqueness.py`
- Updated:
  - `.github/workflows/ci.yml` contracts list.

6. Follow-up hardening after full-suite replay

- `scripts/verify_all.sh`
  - only derives `DB_URL_TEMPLATE` when runtime itself reports a non-empty template.
  - skips `S7 (Multi-Tenancy)` when runtime is `db-per-tenant-org` but `database_url_template` is missing.
  - avoids forcing scripts into non-existent tenant DBs in idonly-style deployments.
- `scripts/verify_mbom_convert.sh`
  - in `db-per-tenant-org` / `db-per-tenant` mode, keeps provided `DB_URL` if present.
  - only falls back to `resolve_database_url()` when `DB_URL` is missing.
- Added CI contract:
  - `src/yuantus/meta_engine/tests/test_ci_contracts_verify_mbom_convert_db_url_fallback.py`

## Verification

Contracts:

```bash
./.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_*.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_db_cli_identity_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_*.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_*.py \
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
  src/yuantus/meta_engine/tests/test_perf_*.py \
  src/yuantus/meta_engine/tests/test_readme_runbook*.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_*.py
```

Result:

- `62 passed in 1.31s`

Runtime checks (key):

- `verify_all.sh` preflight now logs:
  - `START_DEDUP_STACK=1: detected healthy existing stack; reusing current services.`
  - no immediate failure on `59000` bind conflicts.
- Targeted previously-failing scripts in correct runtime DB context:
  - `scripts/verify_bom_effectivity.sh`: `PASS`
  - `scripts/verify_eco_advanced.sh`: `PASS`
  - `USE_DOCKER_WORKER=1 scripts/verify_cad_dedup_relationship_s3.sh`: `PASS`
  - `scripts/verify_mbom_convert.sh`: `PASS`
  - `scripts/verify_version_files.sh` with `YUANTUS_DATABASE_URL` + `YUANTUS_IDENTITY_DATABASE_URL` + `YUANTUS_TENANCY_MODE=db-per-tenant-org`: `PASS`
- Full-suite replay:
  - command: `RUN_DEDUP=1 START_DEDUP_STACK=1 USE_DOCKER_WORKER=1 bash scripts/verify_all.sh`
  - log: `/tmp/verify_all_dedup_docker_worker_20260216-002237.log`
  - result: `PASS: 41  FAIL: 0  SKIP: 47` (`ALL TESTS PASSED`)
  - notable skip: `S7 (Multi-Tenancy)` skipped when runtime template is missing (`db-per-tenant-org runtime missing database_url_template`), preventing false-negative failures on non-isolated runtime configs.

## Notes

- `scripts/verify_multitenancy.sh` may still fail under `yuantusplm_idonly` runtime if environment itself does not enforce expected tenant/org physical isolation semantics for that check (environment issue, not addressed in this patch).
