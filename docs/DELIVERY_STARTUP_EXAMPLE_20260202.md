# Delivery Startup Example (2026-02-02)

This example uses the standard single-tenant compose file.

## 1) Prepare environment

```bash
cd YuantusPLM-Delivery
cp env/.env.example env/.env
# edit env/.env as needed
```

## 2) Start services

```bash
cd compose
# docker compose --env-file ../env/.env up -d
```

## 3) Run migrations (if needed)

```bash
cd ../scripts
./mt_migrate.sh
```

## 4) Basic checks

- Confirm containers are running: `docker ps`
- Review logs if needed: `docker logs <container>`

## 5) Optional verification

```bash
./verify_run_h.sh
```
