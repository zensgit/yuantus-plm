# Delivery Rollback Guide (2026-02-02)

## 1) Preparation

- Ensure you have a valid backup (DB + storage).
- Identify the previous stable package version.

## 2) Stop services

```bash
cd YuantusPLM-Delivery/compose
# docker compose down
```

## 3) Restore backups

- Restore database from backup.
- Restore object storage if applicable.

## 4) Deploy previous package

- Extract the previous delivery bundle.
- Copy your `env/.env` and custom configs.

## 5) Start services

```bash
cd compose
# docker compose --env-file ../env/.env up -d
```

## 6) Verify

- Run quick acceptance: `docs/DELIVERY_QUICK_ACCEPTANCE_20260202.md`
- Validate core workflows.

## Notes

- If you use Alembic downgrade, ensure the target revision is compatible with your data.
- Prefer restoring from backup for safest rollback.
