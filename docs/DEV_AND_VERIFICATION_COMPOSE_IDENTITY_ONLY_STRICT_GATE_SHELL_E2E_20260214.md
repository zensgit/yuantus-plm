# Dev & Verification Report - Compose Identity-only Migrations + Strict Gate Shell E2E (2026-02-14)

This delivery makes private deployment more “decision-complete” for true split databases:

- `docker-compose.yml` runs **identity-only migrations** by default (auth + audit only).
- Strict gate CI includes **evidence-grade shell E2Es** (Run H API-only + identity-only migrations).

## Changes

### 1) Compose: identity-only migrations by default (with escape hatch)

- `docker-compose.yml`
  - New env: `YUANTUS_IDENTITY_MIGRATIONS_MODE` (default: `identity-only`)
  - Startup behavior when `YUANTUS_IDENTITY_DATABASE_URL` is non-empty:
    - `identity-only` (default): `yuantus db upgrade --identity-only`
    - `full` (legacy): `yuantus db upgrade --identity`

### 2) API image includes identity-only Alembic inputs

- `Dockerfile`
  - Copy `alembic.identity.ini` + `migrations_identity/` into the API image so `yuantus db upgrade --identity-only` can run inside containers.

### 3) Strict gate: include shell E2Es (CI enabled)

- `scripts/strict_gate_report.sh`
  - New optional steps in the report:
    - `verify_run_h_e2e` (enabled by `RUN_RUN_H_E2E=1`)
    - `verify_identity_only_migrations` (enabled by `RUN_IDENTITY_ONLY_MIGRATIONS_E2E=1`)
- `.github/workflows/strict-gate.yml`
  - Enable both steps by default in CI strict gate runs.
- `docs/RUNBOOK_STRICT_GATE.md`
  - Document the new env flags and how to run them locally.

### 4) CI change-scope + smoke coverage for identity-only migrations

- `.github/workflows/ci.yml`
  - Change detection includes `alembic.identity.ini` and `migrations_identity/*`
  - `plugin-tests` job runs identity-only migrations smoke:
    - `python -m alembic -c alembic.identity.ini upgrade head`
- `.github/workflows/regression.yml`
  - Change detection includes `alembic.identity.ini` and `migrations_identity/*`

## Verification (Executed)

### 1) Run H API-only E2E (local)

```bash
bash scripts/verify_run_h_e2e.sh | tee tmp/verify_run_h_e2e_20260214-174502.log
```

Evidence:

- Log: `tmp/verify_run_h_e2e_20260214-174502.log`
- Payloads: `tmp/verify-run-h/20260214-174502/`

### 2) Identity-only migrations E2E (local)

```bash
OUT_DIR=tmp/verify-identity-only-migrations/20260214-174518 \
  bash scripts/verify_identity_only_migrations.sh | tee tmp/verify_identity_only_migrations_20260214-174518.log
```

Evidence:

- Log: `tmp/verify_identity_only_migrations_20260214-174518.log`
- Payloads: `tmp/verify-identity-only-migrations/20260214-174518/`

### 3) Strict gate report includes shell E2Es (local)

```bash
RUN_ID=STRICT_GATE_LOCAL_20260214-174534 \
OUT_DIR=tmp/strict-gate/STRICT_GATE_LOCAL_20260214-174534 \
REPORT_PATH=docs/DAILY_REPORTS/STRICT_GATE_LOCAL_20260214-174534.md \
RUN_RUN_H_E2E=1 RUN_IDENTITY_ONLY_MIGRATIONS_E2E=1 \
  bash scripts/strict_gate_report.sh | tee tmp/verify_strict_gate_report_20260214-174534.log
```

Evidence:

- Log: `tmp/verify_strict_gate_report_20260214-174534.log`
- Report: `docs/DAILY_REPORTS/STRICT_GATE_LOCAL_20260214-174534.md`
- Logs: `tmp/strict-gate/STRICT_GATE_LOCAL_20260214-174534/`

### 4) Compose up + identity DB table contract (Postgres) (local)

```bash
docker compose -p yuantusplm_idonly -f docker-compose.yml up -d --build
curl -fsS http://127.0.0.1:7910/api/v1/health > tmp/verify-compose-identity-only/20260214-174937/health.json
docker compose -p yuantusplm_idonly -f docker-compose.yml exec -T postgres \
  psql -U yuantus -d yuantus_identity -c "\\dt" \
  > tmp/verify-compose-identity-only/20260214-174937/identity_tables.txt
docker compose -p yuantusplm_idonly -f docker-compose.yml exec -T postgres \
  psql -U yuantus -d yuantus_identity -c "select tablename from pg_tables where schemaname='public' and tablename like 'meta_%' order by tablename;" \
  > tmp/verify-compose-identity-only/20260214-174937/identity_meta_tables.txt
docker compose -p yuantusplm_idonly -f docker-compose.yml exec -T postgres \
  psql -U yuantus -d yuantus_identity -c "select version_num from alembic_version;" \
  > tmp/verify-compose-identity-only/20260214-174937/identity_alembic_version.txt
```

Evidence:

- Payloads: `tmp/verify-compose-identity-only/20260214-174937/`
  - `compose_up.log`
  - `health.json`
  - `identity_tables.txt`
  - `identity_meta_tables.txt` (expected: 0 rows)
  - `identity_alembic_version.txt` (expected: `i1b2c3d4e5f6`)

