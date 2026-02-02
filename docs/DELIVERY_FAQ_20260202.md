# Delivery FAQ (2026-02-02)

## Q: Where do I put secrets?
A: In your copied env file (e.g. `env/.env`). Do not edit templates directly.

## Q: How do I provide offline images?
A: Place Docker image tarballs under `images/` and load with `docker load -i`.

## Q: Where do TLS certs go?
A: Place `tls.crt` and `tls.key` under `certs/`.

## Q: How do I verify the package integrity?
A: Run `scripts/verify_package.sh` inside `YuantusPLM-Delivery/`.
