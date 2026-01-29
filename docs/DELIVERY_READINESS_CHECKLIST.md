# Delivery Readiness Checklist (Private Deployment)

This checklist summarizes the **must-have**, **optional**, and **risk** items for delivering YuantusPLM.

## A) Must‑Have (交付必配)

### Infrastructure
- [ ] PostgreSQL reachable (read/write)
- [ ] MinIO / S3 storage reachable
- [ ] `YUANTUS_SCHEMA_MODE=migrations`
- [ ] `YUANTUS_TENANCY_MODE=db-per-tenant-org` (if multi‑tenant)

### Core Services
- [ ] `api` and `worker` healthy (`/api/v1/health` = 200)
- [ ] `yuantus db upgrade` executed
- [ ] `yuantus init-storage` executed

### Security
- [ ] `AUTH_MODE=required` in production
- [ ] Tenant/org headers enforced
- [ ] Platform admin enabled only when provisioning (`YUANTUS_PLATFORM_ADMIN_ENABLED=true`)

### Verification
- [ ] `scripts/verify_run_h.sh` passed
- [ ] `scripts/verify_permissions.sh` passed
- [ ] `scripts/verify_product_detail.sh` passed

## B) Optional (可选增强)

- [ ] UI Aggregation regression (`RUN_UI_AGG=1 scripts/verify_all.sh`)
- [ ] Config variants (`RUN_CONFIG_VARIANTS=1 scripts/verify_all.sh`)
- [ ] CAD Pipeline S3 (`scripts/verify_cad_pipeline_s3.sh`)
- [ ] CAD 2D/3D connector coverage scripts
- [ ] Audit logs enable (`YUANTUS_AUDIT_ENABLED=true`)

## C) Risks / Watch‑outs

- [ ] CAD extractors & external services not running (expected SKIP)
- [ ] S3 public endpoint not reachable by clients
- [ ] Schema drift if DB migrations not applied per tenant
- [ ] Legacy relationship tables (ensure Relationship-as-Item migration completed)

## D) Recommended Deployment Commands

```bash
# infra
docker compose up -d postgres minio

# migrations
yuantus db upgrade
./scripts/mt_migrate.sh

# storage
yuantus init-storage

# app
docker compose up -d --build api worker
```

## E) Verification Bundle

```bash
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_permissions.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1
```

Optional full suite:

```bash
RUN_UI_AGG=1 RUN_CONFIG_VARIANTS=1 bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```
