# 校验命令合集（外部交付用，2026-02-03 baseline，2026-04-07 refresh）

> 说明：本文档为外部交付材料，不随交付包一起打包。
> 本次刷新只更新「外部接收方先验证哪些 authoritative entry-point 文档存在」，
> 不引入新的脚本，不要求外部环境运行 pytest，不改 src/、tests、migrations。

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

## 4) 核对基础发布文档

```bash
ls -1 docs/DELIVERY_PACKAGE_NOTE_20260203.md \
  docs/DELIVERY_SUMMARY_20260202.md \
  docs/VERIFICATION_RESULTS.md
```

## 5) 核对当前已闭合的高层 closure 入口（authoritative entry points）

外部验证时**先**确认下列三条 closure 主线的 authoritative entry-point
文档都在交付包内并路径正确。这些是接收方在评估「这一版到底交付了什么」
时应当**首先打开**的文档；其余 per-line / per-package 文档由对应 reading
guide 一层导航即可查到。

### 5a) Subcontracting closure pack（C13）

```bash
ls -1 \
  docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_CONTRACT_SURPASS_MASTER_FINAL_SUMMARY_20260401.md \
  docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_CONTRACT_SURPASS_MASTER_FINAL_SUMMARY_20260401.md \
  docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_OPERATIONAL_READINESS_MASTER_SUMMARY_20260403.md \
  docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_OPERATIONAL_READINESS_MASTER_SUMMARY_20260403.md \
  docs/SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md \
  docs/SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md \
  docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md \
  docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md
```

接收方阅读顺序：先 master final summary（design + verification），再
operational readiness master summary，最后是 launch checklist + operator
runbook。

### 5b) Manufacturing routing / workcenter closure

```bash
ls -1 \
  docs/DESIGN_PARALLEL_MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_FINAL_SUMMARY_20260403.md \
  docs/DEV_AND_VERIFICATION_PARALLEL_MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_FINAL_SUMMARY_20260403.md \
  docs/MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_READING_GUIDE_20260403.md
```

接收方阅读顺序：先 final summary（design + verification），再 reading
guide。

### 5c) Odoo18-inspired reference parity round

```bash
ls -1 \
  docs/DESIGN_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md \
  docs/DEV_AND_VERIFICATION_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md \
  docs/ODOO18_REFERENCE_PARITY_READING_GUIDE_20260407.md
```

接收方阅读顺序：先 final summary（design + verification），再 reading
guide；该 reading guide 内含七条已闭合子线（doc-sync checkout governance,
breakage helpdesk traceability, ECO BOM compare mode integration, workflow
custom action predicate upgrade, ECO suspension gate, ECO activity chain
→ release readiness linkage, document sync mirror compatibility）的二级
导航，外部验证时不需要逐条检查每个 per-package 文档。

### 5d) 校验文档索引存在并包含上述入口

```bash
ls -1 docs/DELIVERY_DOC_INDEX.md
grep -F "ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407" docs/DELIVERY_DOC_INDEX.md
grep -F "MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_FINAL_SUMMARY_20260403" docs/DELIVERY_DOC_INDEX.md
grep -F "C13_SUBCONTRACTING_CONTRACT_SURPASS_MASTER_FINAL_SUMMARY_20260401" docs/DELIVERY_DOC_INDEX.md
```

每条 `grep` 至少应当返回一行；如有任何一条返回空，请联系交付方确认包是否
完整。

## 6) 可选：运行快速验证脚本

```bash
cd /tmp/yuantus_delivery/YuantusPLM-Delivery
bash scripts/verify_run_h.sh
```

## 7) 验证完成判定

外部验证可以判定为「通过」的最低要求：

1. §1 sha256 校验通过；
2. §3 包内 manifest 校验通过；
3. §4 基础发布文档存在；
4. §5a / §5b / §5c 三组 `ls -1` 全部成功（即所有 authoritative entry-point
   文档都在包内）；
5. §5d 中三条 `grep` 全部命中；
6. （可选）§6 验证脚本无报错。

满足以上条件即代表当前交付包包含三条主线的完整 closure 入口文档，与
2026-04-07 内部 closure 状态一致。
