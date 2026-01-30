# YuantusPLM (元图PLM)

[![Release](https://img.shields.io/github/v/release/zensgit/yuantus-plm?display_name=tag)](https://github.com/zensgit/yuantus-plm/releases)
[![License](https://img.shields.io/github/license/zensgit/yuantus-plm)](LICENSE)

Repository name: `yuantus-plm`  
Product name: **YuantusPLM / 元图PLM**

This repo contains the **core PLM service** (modular monolith) and contracts to integrate with:
- `Athena` (ECM/DMS)
- `cad-ml-platform` (CAD ML analysis)
- `dedupcad-vision` (drawing deduplication)

## Quick start (dev)

1) Start dependencies (infra only):
```bash
docker compose up -d postgres minio
```

2) Run API:
```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -e .
yuantus start --reload
```

API: `http://localhost:7910/api/v1/health`

Notes:
- Postgres (docker) exposed at `localhost:55432`
- MinIO (docker) exposed at `localhost:59000` (S3 API) / `localhost:59001` (Console)

## Quick start (docker)

Run API + Worker + Postgres + MinIO via docker compose:

```bash
docker compose up --build
```

## Auth (dev)

Default is `YUANTUS_AUTH_MODE=optional` (backward compatible).

Seed identity (tenant/org/user) and login:
```bash
yuantus seed-identity --tenant tenant-1 --org org-1 --username admin --password admin --user-id 1 --roles admin
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}'
```

Multi-org flow (login without org → list orgs → switch org token):
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s http://127.0.0.1:7910/api/v1/auth/orgs -H "Authorization: Bearer $TOKEN"
ORG_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/switch-org \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"org_id":"org-1"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

To require JWT globally (except `GET /api/v1/health`, `POST /api/v1/auth/login`, and docs):
```bash
export YUANTUS_AUTH_MODE=required
```

## Verification

See `docs/VERIFICATION.md`.

## Runbooks

- `docs/RUNBOOK_JOBS_DIAG.md` (Jobs/CAD failure diagnostics)
- `docs/ERROR_CODES_JOBS.md` (Jobs error codes)

## Development design

See `docs/DEVELOPMENT_DESIGN.md`.

## Development plan

See `docs/DEVELOPMENT_PLAN.md`.

## Private delivery acceptance

See `docs/PRIVATE_DELIVERY_ACCEPTANCE.md`.

## Reuse guide

See `docs/REUSE.md` (how to reuse `/Users/huazhou/Downloads/Github/PLM/src`).

## Contributing

See `CONTRIBUTING.md`.

## Security

See `SECURITY.md`.

## Conventions

- **Python package**: `yuantus` (`src/yuantus/`)
- **CLI**: `yuantus ...` (legacy alias: `plm ...`)
- **Tenant header**: `x-tenant-id`
- **Organization header**: `x-org-id`

## Runtime

- **Python**: 3.10+ (recommended 3.11)
