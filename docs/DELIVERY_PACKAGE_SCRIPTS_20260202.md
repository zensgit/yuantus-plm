# Delivery Package Scripts (2026-02-02)

## Build Archive (tar.gz)

```bash
# From repo root
export PKG_NAME=yuantus-plm_20260202

git ls-files -z | xargs -0 tar -czf ${PKG_NAME}.tar.gz
sha256sum ${PKG_NAME}.tar.gz > ${PKG_NAME}.tar.gz.sha256
```

## Build Archive (zip)

```bash
# From repo root
export PKG_NAME=yuantus-plm_20260202

git ls-files -z | xargs -0 zip -q ${PKG_NAME}.zip
sha256sum ${PKG_NAME}.zip > ${PKG_NAME}.zip.sha256
```

## Verify Archive

```bash
sha256sum -c ${PKG_NAME}.tar.gz.sha256
sha256sum -c ${PKG_NAME}.zip.sha256
```

## Verify Manifest Against Files

```bash
# Compare manifest hashes with current checkout
sha256sum -c docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt
```
