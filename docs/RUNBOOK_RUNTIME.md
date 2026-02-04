# YuantusPLM Runtime/Deployment Runbook

This runbook describes how to run the stack with db-per-tenant-org and audit,
and how to roll back safely.

## Scope

- Start/stop docker compose stack
- Enable db-per-tenant-org tenancy
- Enable audit logging
- Roll back to single-tenant or disable audit

## Prerequisites

- Docker Desktop running
- `docker compose` available
- Repo root has `.env`

## CAD extractor in compose

The docker compose stack includes the CAD extractor service. The API/Worker
containers use `http://cad-extractor:8200` by default. If you want to disable
external extraction, set `YUANTUS_CAD_EXTRACTOR_MODE=optional` (or clear the
base URL) and restart the stack.

## Enable db-per-tenant-org + audit (docker compose)

1) Ensure `.env` includes:

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@postgres:5432/yuantus_mt_pg__{tenant_id}__{org_id}
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@postgres:5432/yuantus_identity_mt_pg
YUANTUS_AUDIT_ENABLED=true
```

2) Create tenant/org databases (once per environment):

```bash
bash scripts/mt_pg_bootstrap.sh
```

3) Run migrations for identity and tenant/org databases:

```bash
MODE=db-per-tenant-org \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/mt_migrate.sh
```

4) Start or restart services:

```bash
docker compose -p yuantusplm up -d --build
```

5) Verify:

```bash
curl -s http://127.0.0.1:7910/api/v1/health -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
RUN_CAD_EXTRACTOR_SERVICE=1 bash scripts/verify_all.sh
```

## Roll back to single-tenant

1) Update `.env`:

```bash
YUANTUS_TENANCY_MODE=single
YUANTUS_DATABASE_URL_TEMPLATE=
YUANTUS_IDENTITY_DATABASE_URL=
```

2) Restart services:

```bash
docker compose -p yuantusplm up -d --build
```

Notes:
- Multi-tenant data remains in `yuantus_mt_pg__*` databases.
- Single-tenant data remains in `yuantus` database.
- Switching modes does not merge data.

## Roll back audit only

1) Update `.env`:

```bash
YUANTUS_AUDIT_ENABLED=false
```

2) Restart services:

```bash
docker compose -p yuantusplm up -d --build
```

Notes:
- Existing audit rows remain in the database.
- Disabling audit stops new audit writes.

## Stop services

```bash
docker compose -p yuantusplm down
```

## Repo cache cleanup (optional)

```bash
bash scripts/cleanup_repo_caches.sh
```

## Ops FAQ

### Q: cad-ml 端口冲突怎么办？
默认脚本使用 `18000/19090/16379`。可在启动前覆盖端口：

```bash
CAD_ML_API_PORT=18010 CAD_ML_API_METRICS_PORT=19091 CAD_ML_REDIS_PORT=16380 \
  scripts/run_cad_ml_docker.sh
```

排查占用：

```bash
lsof -nP -iTCP:18000 -sTCP:LISTEN
```

### Q: docker compose 提示 “Found orphan containers”？
这是旧 compose 项目遗留容器。可在停止时清理：

```bash
CAD_ML_REMOVE_ORPHANS=1 scripts/stop_cad_ml_docker.sh
```

或手动执行：

```bash
docker compose -f /path/to/compose.yml down --remove-orphans
```
