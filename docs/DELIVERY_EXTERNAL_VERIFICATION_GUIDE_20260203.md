# External Verification Guide (2026-02-03)

This guide is intended for third-party or offline validation of the delivery package.

## 1) Verify package checksums

```bash
# Linux
sha256sum -c YuantusPLM-Delivery_20260203.tar.gz.sha256
sha256sum -c YuantusPLM-Delivery_20260203.zip.sha256

# macOS
shasum -a 256 -c YuantusPLM-Delivery_20260203.tar.gz.sha256
shasum -a 256 -c YuantusPLM-Delivery_20260203.zip.sha256
```

## 2) Extract the package

```bash
mkdir -p /tmp/yuantus_delivery
# tar.gz
tar -xzf YuantusPLM-Delivery_20260203.tar.gz -C /tmp/yuantus_delivery
# or zip
# unzip -q YuantusPLM-Delivery_20260203.zip -d /tmp/yuantus_delivery
```

## 3) Verify file manifest (integrity of contents)

```bash
cd /tmp/yuantus_delivery/YuantusPLM-Delivery
# Linux
sha256sum -c docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt
# macOS
shasum -a 256 -c docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt
```

## 4) Spot-check key docs

- `docs/DELIVERY_SUMMARY_20260202.md`
- `docs/DELIVERY_PACKAGE_NOTE_20260203.md`
- `docs/VERIFICATION_RESULTS.md`

## 5) Optional smoke verification

```bash
cd /tmp/yuantus_delivery/YuantusPLM-Delivery
# If TENANCY_MODE=db-per-tenant / db-per-tenant-org, run tenant migrations first
MIGRATE_TENANT_DB=1 bash scripts/verify_run_h.sh
```

If any checksum or manifest verification fails, stop and request a fresh package copy.
