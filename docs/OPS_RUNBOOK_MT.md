# YuantusPLM Multi-Tenancy Ops Runbook

## Scope

This runbook covers **db-per-tenant-org** operations for private deployments:

- Start/stop
- Migrations
- Tenant provisioning
- Backup/restore
- Health & monitoring
- Troubleshooting

> Baseline: PostgreSQL + MinIO + Docker Compose.

---

## 0) Environment Checklist

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg

export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:9000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:9000'
```

---

## 1) Start/Stop (Compose)

```bash
# Base infra
docker compose up -d postgres minio

# App
docker compose up -d --build api worker
```

Check health:

```bash
curl -s http://127.0.0.1:7910/api/v1/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 2) Migrations (Multi‑Tenancy)

### 2.1 Bootstrap identity DB

```bash
yuantus db upgrade
```

### 2.2 Apply multi‑tenant schemas

```bash
./scripts/mt_migrate.sh
```

### 2.3 Verify

```bash
psql "$YUANTUS_IDENTITY_DATABASE_URL" -c "\dt" | head
```

---

## 3) Tenant Provisioning

Enable platform admin:

```bash
export YUANTUS_PLATFORM_ADMIN_ENABLED=true
```

Create tenant/org:

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/admin/tenants \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: platform' -H 'x-org-id: platform' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","admin_username":"admin","admin_password":"admin"}'
```

Verify:

```bash
curl -s http://127.0.0.1:7910/api/v1/admin/tenant \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 4) Backup & Restore

### 4.1 Backup

```bash
bash scripts/backup.sh
```

Artifacts are stored under `./backups/` by default.

### 4.2 Restore

```bash
bash scripts/restore.sh <backup_dir>
```

### 4.3 Verify

```bash
bash scripts/verify_backup_restore.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 5) Monitoring & Health

### 5.1 Health endpoints

```bash
curl -s http://127.0.0.1:7910/api/v1/health
curl -s http://127.0.0.1:7910/api/v1/health/deps
```

### 5.2 Ops hardening checks

```bash
bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

---

## 6) Common Issues

### 6.1 Missing tenant/org context

Error:

```
TENANCY_MODE=db-per-tenant-org requires org_id context
```

Fix: ensure all requests include `x-tenant-id` and `x-org-id` headers.

### 6.2 Migration conflicts

- If `alembic_version` missing in tenant DB, run:

```bash
yuantus db upgrade
```

- If schema drift suspected, re‑run:

```bash
./scripts/mt_migrate.sh
```

### 6.3 S3 download fails

- Ensure `YUANTUS_S3_PUBLIC_ENDPOINT_URL` is reachable from clients.
- Validate presigned URL via `curl -I`.

---

## 7) Verification Checklist (Minimal)

```bash
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_permissions.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 8) References

- `docs/VERIFICATION.md`
- `docs/VERIFICATION_RESULTS.md`
- `docs/S7_MULTITENANCY_VERIFICATION.md`
