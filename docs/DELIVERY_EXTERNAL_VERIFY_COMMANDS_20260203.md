# 校验命令合集（外部交付用，2026-02-03）

> 说明：本文档为外部交付材料，不随交付包一起打包。

## 1) 校验交付包 sha256

```bash
# Linux
sha256sum -c YuantusPLM-Delivery_20260203.tar.gz.sha256
sha256sum -c YuantusPLM-Delivery_20260203.zip.sha256

# macOS
shasum -a 256 -c YuantusPLM-Delivery_20260203.tar.gz.sha256
shasum -a 256 -c YuantusPLM-Delivery_20260203.zip.sha256
```

## 2) 解压交付包

```bash
mkdir -p /tmp/yuantus_delivery
# tar.gz
tar -xzf YuantusPLM-Delivery_20260203.tar.gz -C /tmp/yuantus_delivery
# or zip
# unzip -q YuantusPLM-Delivery_20260203.zip -d /tmp/yuantus_delivery
```

## 3) 校验包内容清单

```bash
cd /tmp/yuantus_delivery/YuantusPLM-Delivery
# Linux
sha256sum -c docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt
# macOS
shasum -a 256 -c docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt
```

## 4) 核对关键文档

```bash
ls -1 docs/DELIVERY_PACKAGE_NOTE_20260203.md \
  docs/DELIVERY_SUMMARY_20260202.md \
  docs/VERIFICATION_RESULTS.md
```

## 5) 可选：运行快速验证脚本

```bash
cd /tmp/yuantus_delivery/YuantusPLM-Delivery
bash scripts/verify_run_h.sh
```
