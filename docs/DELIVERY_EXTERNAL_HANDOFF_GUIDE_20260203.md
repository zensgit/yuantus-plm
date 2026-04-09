# 对外交付包说明（2026-02-03 baseline，2026-04-07 refresh）

> 说明：本文档为外部交付材料，不随交付包一起打包。
> 本次刷新只更新「外部交付包当前状态 / 接收方先看哪些 authoritative 入口文档」，
> 不改 src/、tests、migrations，不引入新的脚本或交付物。

## 交付物清单

1) 交付包文件（任选其一或同时提供）
- `YuantusPLM-Delivery_20260203.tar.gz`
- `YuantusPLM-Delivery_20260203.zip`

2) 校验文件（与交付包同目录）
- `YuantusPLM-Delivery_20260203.tar.gz.sha256`
- `YuantusPLM-Delivery_20260203.zip.sha256`

3) 外部校验材料（不在交付包内）
- `docs/DELIVERY_PACKAGE_HASHES_20260203.md`（对外哈希清单）
- `docs/DELIVERY_EXTERNAL_VERIFY_COMMANDS_20260203.md`（校验命令合集）

## 当前已闭合的高层交付状态（截至 2026-04-07）

外部接收方在评估交付包时，需要知道以下三条主线已经各自完成 **closure +
final summary + reading guide / runbook** 三件套，没有已知 blocking gap。
这些是审阅交付包的 **authoritative entry points**：

### A. Subcontracting closure pack（C13）

最权威的三个入口，按推荐阅读顺序：

1. `docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_CONTRACT_SURPASS_MASTER_FINAL_SUMMARY_20260401.md`
   — subcontracting contract surpass master final summary（design 侧总收口）
2. `docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_CONTRACT_SURPASS_MASTER_FINAL_SUMMARY_20260401.md`
   — verification 侧总收口
3. `docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_OPERATIONAL_READINESS_MASTER_SUMMARY_20260403.md`
   + `docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_OPERATIONAL_READINESS_MASTER_SUMMARY_20260403.md`
   — operational readiness master summary

发布 / 上线相关：

- `docs/SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md` —
  launch checklist signoff pack（外部上线 sign-off 用）
- `docs/SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md` —
  operator runbook + daily review playbook
- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md`
- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md`

### B. Manufacturing routing / workcenter closure

权威入口，按推荐阅读顺序：

1. `docs/DESIGN_PARALLEL_MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_FINAL_SUMMARY_20260403.md`
   — design 侧 final summary
2. `docs/DEV_AND_VERIFICATION_PARALLEL_MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_FINAL_SUMMARY_20260403.md`
   — verification 侧 final summary
3. `docs/MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_READING_GUIDE_20260403.md`
   — reading guide（导航文档）

### C. Odoo18-inspired reference parity round

权威入口，按推荐阅读顺序：

1. `docs/DESIGN_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md`
   — design 侧 final summary（七条子线 closure 收口）
2. `docs/DEV_AND_VERIFICATION_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md`
   — verification 侧 final summary
3. `docs/ODOO18_REFERENCE_PARITY_READING_GUIDE_20260407.md`
   — reading guide（七条子线导航）

七条已闭合的 Odoo18-inspired 子线（每条都有自己的 final summary +
reading guide，详见上面的 reading guide）：

- doc-sync checkout governance enhancement
- breakage helpdesk traceability enhancement
- ECO BOM compare mode integration
- workflow custom action predicate upgrade
- ECO suspension gate
- ECO activity chain → release readiness linkage
- document sync mirror compatibility

## 推荐交付流程

1) 提供交付包与 `.sha256` 校验文件。
2) 附带本说明与校验命令合集，确保外部接收方能独立完成验证。
3) 提醒接收方在解压后按包内文档验证：
   - `docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt`（包内容清单）
   - `docs/DELIVERY_EXTERNAL_VERIFICATION_GUIDE_20260203.md`（包内验证指引）
4) 同时把上文 §当前已闭合的高层交付状态 中列出的 authoritative
   entry-point 文档清单交给接收方，作为「先看哪些文档」的导航。

## 外部接收方校验步骤（摘要）

1) 校验交付包完整性（对比 `.sha256`）。
2) 解压交付包。
3) 使用包内清单文件进行内容核验。
4) 按 §当前已闭合的高层交付状态 中列出的 authoritative entry-point 顺序
   阅读 design + verification final summary，再按需要查阅各自的 reading
   guide / runbook。
5) 如需，执行包内脚本进行快速验证。

## Authoritative entry-point 一句话总览

- **Subcontracting**：`MASTER_FINAL_SUMMARY_20260401` + `OPERATIONAL_READINESS_MASTER_SUMMARY_20260403`
  + `LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403`
  + `OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403`
- **Manufacturing routing / workcenter**：`MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_FINAL_SUMMARY_20260403`
  + `MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_READING_GUIDE_20260403`
- **Odoo18 parity**：`ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407`
  + `ODOO18_REFERENCE_PARITY_READING_GUIDE_20260407`

以上是外部接收方应当首先打开的文档。其余 per-line / per-package 文档由对应
reading guide 一层导航即可查到。

## 异常处理

- 如校验失败，请停止使用并申请重新下发交付包。
- 如需确认版本，请以 `docs/DELIVERY_PACKAGE_NOTE_20260203.md` 与哈希清单为准。
- 如对某条 closure 是否真的闭合存疑，以对应 final summary 的「Closure
  Statement」段落为准；任何 reading guide 都只是导航，不会修改 closure 结论。
