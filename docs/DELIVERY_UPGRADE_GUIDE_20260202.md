# Delivery Upgrade Guide (2026-02-02)

## 1) Preparation

- Backup DB and storage before upgrade.
- Read `docs/DELIVERY_CHANGELOG_20260202.md` for changes.

## 2) Stop services

```bash
cd YuantusPLM-Delivery/compose
# docker compose down
```

## 3) Replace package

- Extract the new delivery package to a fresh directory.
- Copy your env file (`env/.env`) and any custom configs.

## 4) Run migrations

```bash
cd ../scripts
./mt_migrate.sh
```

## 5) Start services

```bash
cd ../compose
# docker compose --env-file ../env/.env up -d
```

## 6) Verify

- Run quick acceptance: `docs/DELIVERY_QUICK_ACCEPTANCE_20260202.md`
- Check logs and health endpoints
