# Delivery Acceptance Guide (2026-02-02)

## 1) Verify Package Integrity

```bash
cd /Users/huazhou/Downloads/Github/Yuantus/YuantusPLM-Delivery
sha256sum -c YuantusPLM-Delivery_20260203.tar.gz.sha256
sha256sum -c YuantusPLM-Delivery_20260203.zip.sha256
```

## 2) Extract

```bash
# tar.gz
mkdir -p /tmp/yuantus_delivery
 tar -xzf YuantusPLM-Delivery_20260203.tar.gz -C /tmp/yuantus_delivery

# zip
unzip -q YuantusPLM-Delivery_20260203.zip -d /tmp/yuantus_delivery
```

## 3) Review Contents

```bash
ls -la /tmp/yuantus_delivery/YuantusPLM-Delivery
```

Key folders:
- `compose/`: docker-compose base + overlays
- `env/`: env templates (no secrets)
- `scripts/`: migration/backup/verification helpers
- `docs/`: runbooks and verification logs

## 4) Configure Environment

Copy an env template and adjust:

```bash
cd /tmp/yuantus_delivery/YuantusPLM-Delivery
cp env/.env.example env/.env
```

## 5) Start (Example)

```bash
cd /tmp/yuantus_delivery/YuantusPLM-Delivery/compose
# baseline single-tenant example
# docker compose --env-file ../env/.env up -d
```

## 6) Post-Start Checks

- Confirm services are up (`docker ps`).
- Use scripts in `scripts/` for migrations and verification when needed.
- If `TENANCY_MODE=db-per-tenant` / `db-per-tenant-org`, run tenant migrations before smoke verification: `scripts/migrate_tenant_db.sh tenant-1 org-1` (or `MIGRATE_TENANT_DB=1 bash scripts/verify_run_h.sh`).

## References

- `docs/OPS_RUNBOOK_MT.md`
- `docs/DELIVERY_READINESS_CHECKLIST.md`
- `docs/VERIFICATION_RESULTS.md`
