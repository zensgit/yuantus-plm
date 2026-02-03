# Delivery Quick Acceptance (2026-02-02)

## 1) Verify package integrity

```bash
cd /Users/huazhou/Downloads/Github/Yuantus/YuantusPLM-Delivery
sha256sum -c YuantusPLM-Delivery_20260203.tar.gz.sha256
```

## 2) Extract and inspect

```bash
mkdir -p /tmp/yuantus_delivery
 tar -xzf YuantusPLM-Delivery_20260203.tar.gz -C /tmp/yuantus_delivery
ls -la /tmp/yuantus_delivery/YuantusPLM-Delivery
```

## 3) Minimal start (example)

```bash
cd /tmp/yuantus_delivery/YuantusPLM-Delivery
cp env/.env.example env/.env
cd compose
# docker compose --env-file ../env/.env up -d
```

## 4) Confirm

- `docker ps` shows services running.
- Optional: run `scripts/verify_run_h.sh` for a quick smoke.

## Sign-off

- Customer Representative: ____________________  Date: ____________
- Delivery Owner: _____________________________  Date: ____________
