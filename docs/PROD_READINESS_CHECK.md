# Production Readiness Quick Check

This checklist is a lightweight pre‑deployment sanity check for production readiness.

## 1) Runtime & Ports

- [ ] API listening on `:7910`
- [ ] Health: `GET /api/v1/health` returns 200
- [ ] OpenAPI: `GET /openapi.json` returns 200

## 2) Environment Variables

Required:

- [ ] `YUANTUS_SCHEMA_MODE=migrations`
- [ ] `YUANTUS_TENANCY_MODE=db-per-tenant-org` (if multi‑tenant)
- [ ] `YUANTUS_DATABASE_URL` and `YUANTUS_DATABASE_URL_TEMPLATE`
- [ ] `YUANTUS_IDENTITY_DATABASE_URL`
- [ ] `YUANTUS_STORAGE_TYPE=s3` (if using MinIO/S3)
- [ ] `YUANTUS_S3_ENDPOINT_URL`
- [ ] `YUANTUS_S3_PUBLIC_ENDPOINT_URL`

Security:

- [ ] `YUANTUS_AUTH_MODE=required`
- [ ] `YUANTUS_PLATFORM_ADMIN_ENABLED=false` (after provisioning)

Optional but recommended:

- [ ] `YUANTUS_AUDIT_ENABLED=true`
- [ ] `YUANTUS_QUOTA_MODE=enforce`

## 3) Database & Migrations

- [ ] `yuantus db upgrade` applied
- [ ] `./scripts/mt_migrate.sh` executed for multi‑tenant
- [ ] `alembic_version` exists in tenant DBs

## 4) Storage

- [ ] `yuantus init-storage` executed
- [ ] Presigned URL reachable from client network

## 5) Verification (minimal)

```bash
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_permissions.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1
```

## 6) Observability

- [ ] Logs accessible (`docker logs yuantus-api-1`)
- [ ] Metrics/health endpoints reachable (if enabled)

