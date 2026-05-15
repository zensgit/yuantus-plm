# Yuantus PLM × Odoo18 PLM 关联功能全景与差距分析（20260514，R2）

> **范围**：本文在 `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` 基础上，把比对范围从 `references/odoo18-enterprise-main/addons/` 下 35 个 `plm_*` 扩展，扩展到 Odoo 自身的 PLM 关联模块全集（`mrp_plm` 核心、`mrp_*`、`quality_*`、`maintenance*`、`repair`、`documents*`、`approvals`、`base_automation`、`barcodes` 等）。目的是回答 **"在 Odoo 体系里，跟 PLM 关联的功能有哪些，Yuantus 目前对位状态如何"**。
>
> **修订说明（R2，20260514）**：人工复审指出 R1 多处"GAP"判定与代码现状不符，已在 §三 重新分档（Absent / Prototype exists / Integrated but incomplete），§四 重排断点优先序，并修正 LOC 数字（ECO service 之前误写为 "121K 行"，实测 `wc -l src/yuantus/meta_engine/services/eco_service.py` = **3199 行**；其他子域 LOC 来源同样以 `find … -name '*.py' | xargs wc -l` 为准）。证据均给出文件:行号。
>
> **结构**：
> - 一、PLM 关联模块全景（按四圈分层）
> - 二、`plm_*` 35 个扩展按价值分层
> - 三、Yuantus 现状对位（按 Absent / Prototype exists / Integrated but incomplete 三档）
> - 四、按 PLM 价值链断点排序的最大空缺
> - 五、落地建议（按 per-phase opt-in 规则推进）
>
> **纪律**：每一项建议都按"小 PR + 默认关闭 + 强测试 + 不迁移数据"边界推进，每一项独立 opt-in，不打包。本文只做分析，不携带任何代码改动。

---

## 一、PLM 关联模块全景

Odoo 中"跟 PLM 关联"的模块远不止 `addons/plm_*` 那 35 个扩展，按依赖距离分四圈：

### 圈 1 — PLM 核心域

| Odoo 模块 | 能力 |
|---|---|
| `odoo/addons/mrp_plm` *(core)* | **官方 PLM 主模块**：BOM/产品版本化 + ECO + 按变更类型走不同审批流（`depends: ['mrp']`） |
| `odoo/addons/mrp_workorder_plm` | 把 PLM 版本绑定到工单 worksheet，确保现场用最新图纸 |
| `addons/plm` *(enterprise ext)* | CAD 编辑器集成（SolidWorks / SolidEdge / Inventor / FreeCAD / DraftSight / ThinkDesign / AutoCAD）+ 工程状态机 draft → confirmed → released → obsolete |
| `addons/plm_engineering` | 双 BOM 模式（engineering vs manufacturing） |
| `addons/plm_*` (33 个其他扩展) | 见第二节分层 |

### 圈 2 — 制造执行链（PLM 直接消费方）

PLM 发布出来的 BOM / Routing / Doc 直接喂给这一圈：

| Odoo 模块 | 能力 |
|---|---|
| `mrp` *(core)* | BOM、工艺路线、生产订单基础 |
| `mrp_workorder` *(enterprise)* | 工单 + Gantt 排程 + 实时报工，`depends: ['quality', 'mrp', 'barcodes', 'web_gantt']` |
| `mrp_subcontracting` + 5 个子模块 | 外协生产（含 quality / dropshipping / landed_costs / repair / purchase） |
| `mrp_mps` | **主生产计划 (Master Production Schedule)** |
| `mrp_account` / `mrp_landed_costs` | 制造成本归集 + 落地成本 |
| `mrp_product_expiry` | 物料保质期/有效期 |
| `mrp_workorder_iot` | 工单接 IoT 设备采集 |

### 圈 3 — 质量 / 维护 / 维修（PLM 反馈闭环）

| Odoo 模块 | 能力 |
|---|---|
| `quality` + `quality_control` *(core)* | 质量点、检验单、不合格警报 |
| `quality_control_worksheet` | 检验工序表单化 |
| `quality_mrp` / `quality_mrp_workorder` / `quality_mrp_workorder_worksheet` | **把质检嵌入工单步骤**（PLM 工艺路线 → MES 工单 → 质检点） |
| `quality_iot` / `quality_control_iot` / `quality_mrp_workorder_iot` | IoT 自动采集质检数据 |
| `quality_repair` | 质检结果触发返修 |
| `maintenance` + `maintenance_worksheet` | 设备维护工单 |
| `mrp_maintenance` | **PLM 设备保养绑定到制造工单**（`depends: ['mrp_workorder', 'maintenance']`） |
| `repair` + `mrp_repair` + `purchase_repair` | RMA / 售后返修 + 备件采购 |
| `helpdesk_repair` | 客服工单 → 返修 |
| `addons/plm_breakages` + `addons/plm_ent_breakages_helpdesk` | 现场失效跟踪 + helpdesk 联动 |

### 圈 4 — 文档 / 审批 / 自动化 / 编码（PLM 平台底座）

| Odoo 模块 | 能力 |
|---|---|
| `documents` + `documents_product` | 通用文档管理 + 产品关联（`depends: ['base', 'mail', 'portal', 'web_enterprise', 'attachment_indexation', 'digest']`） |
| `attachment_indexation` | 附件全文索引 |
| `addons/mirror_document_server` | 多站点文档镜像 |
| `approvals` *(core)* | 通用审批流 |
| `approvals_purchase` / `approvals_purchase_stock` | 审批接采购/库存业务 |
| `base_automation` | **事件 → 条件 → 动作**自动化引擎（用户可配置规则） |
| `addons/activity_validation` | 把 ECR/ECO 任务挂到 `mail.activity` 形成多级任务树 |
| `barcodes` + `barcodes_gs1_nomenclature` | 条码 / GS1 命名 |
| `product` / `product_matrix` / `product_images` / `product_expiry` | 产品主数据 / 变体矩阵 / 图片 / 效期 |

### 依赖流向图

```
                  ┌─────────────────────────┐
                  │  documents + approvals  │  ← PLM 底座
                  │  base_automation        │
                  └───────────┬─────────────┘
                              ▼
                  ┌─────────────────────────┐
                  │      mrp_plm            │  ← PLM 核心：ECO + BOM 版本
                  │  + plm_* 扩展 (35)      │
                  └───────────┬─────────────┘
                              ▼
        ┌──────────────────────────────────────────────┐
        ▼                     ▼                        ▼
  ┌──────────┐         ┌──────────────┐         ┌──────────────┐
  │  mrp     │────────▶│ mrp_workorder│────────▶│  quality     │
  │  mrp_mps │         │ + _iot/_plm  │         │  + _control  │
  └──────────┘         └──────────────┘         └──────────────┘
        │                     │                        │
        ▼                     ▼                        ▼
  ┌──────────────┐    ┌──────────────┐         ┌──────────────┐
  │subcontracting│    │  maintenance │         │  repair      │
  │              │    │  + mrp_maint │         │  + helpdesk  │  ← 反馈环回到 PLM
  └──────────────┘    └──────────────┘         └──────────────┘
```

---

## 二、35 个 `plm_*` 扩展按价值分层

### 2.1 HIGH-VALUE（值得借鉴的工作流/算法）

| 模块 | 能力摘要 | 借鉴价值 |
|---|---|---|
| `plm` | 全套 CAD 编辑器集成 + 工程状态机 + checkout/checkin + 设计变更跟踪 | 工作流编排高复用 |
| `activity_validation` | ECR + ECO 状态机 + ECO 父子任务分解（基于 `mail.activity`） | 变更治理闭环 |
| `plm_consumption_plans` | 生产消耗计划 + 方差报表（`template.consumption.plan` + `consumption.state`） | 连接 PLM↔MES↔Cost 的桥 |
| `plm_automated_convertion` | CAD 多格式分布式转换（`plm_convert_servers` + `plm_convert_rule` + `plm_convert_stack`） | 服务器池+规则触发+队列 |
| `plm_pack_and_go` | BOM 一键打包（递归走 BOM 树，按 revision 过滤 2D/3D/规格书，流式 zip） | 供应商交付场景刚需 |
| `plm_engineering` | 双 BOM 生命周期模式 | 工程→制造分离 |

### 2.2 MEDIUM-VALUE（配置与约定模式）

| 模块 | 能力摘要 |
|---|---|
| `plm_automate_normal_bom` | EBOM→MBOM 自动派生 cron |
| `plm_cutted_parts` | 切割物料与边角料追踪 |
| `plm_date_bom` | 时间窗 BOM effectivity |
| `plm_automatic_weight` | BOM 重量级联汇总 |
| `plm_spare` | 备件 BOM / 售后手册 |
| `plm_breakages` | 现场失效记录 |
| `plm_ent_breakages_helpdesk` | breakages 接 helpdesk |
| `plm_document_multi_site` | 多站点文档同步 |
| `plm_box` | 非 CAD 文档容器 |
| `plm_project` | 项目↔产品发布进度联动 |
| `plm_auto_engcode` | 按品类的 `ir.sequence` 编号 |
| `plm_auto_translator` | cron + 翻译 API 填 .po |
| `plm_pdf_workorder` | 技术文档嵌入工单 PDF |
| `plm_workflow_custom_action` | 状态变化触发自动化（依赖 `base_automation`） |
| `plm_bom_summarize` | 多级 BOM 扁平化 |

### 2.3 LOW-VALUE（Odoo UI / 平台胶水，不建议借鉴）

`plm_web_3d` / `plm_web_3d_sale` / `plm_compare_bom` / `plm_web_revision` / `plm_suspended` / `plm_product_only_latest` / `plm_purchase_only_latest` / `plm_sale_only_latest` / `plm_report_language_helper` / `plm_product_description_language_helper` / `plm_pdf_workorder_enterprise` / `plm_client_customprocedure` / `plm_auto_internalref`

这些模块或是 Odoo 前端 widget，或是单字段/单状态扩展，或是 Odoo group/UI 过滤——对应能力在 Yuantus 已有 API 层或权限模型中均能覆盖，重写无收益。

---

## 三、Yuantus 现状对位

> **分档定义**：
> - **Integrated**：能力已成型并与上下游接通，可能仍有边角能力可深化。
> - **Integrated but incomplete**：模型/路由/服务已落地，但缺关键运行时闭环或上下游联动。
> - **Prototype exists**：代码层已有 model/router/service 雏形，但能力薄、未与主链路打通。
> - **Absent**：仓库内无对应实现（grep 零命中或仅有外部 stub）。
>
> **LOC 数字来源**：`find src/yuantus/meta_engine/<domain> -type f -name '*.py' | xargs wc -l`（汇总值，仅作维度参考，**不**等于成熟度）。

### 3.1 Integrated（已成型）

| Odoo 模块族 | Yuantus 对位 | 证据 |
|---|---|---|
| `mrp_plm` + `plm` | `meta_engine/version`（2321 行 + 67 测试，比 Odoo revision mixin 严格）+ ECO service（**3199 行**，非此前误写的 121K）+ `cad_connectors` | `src/yuantus/meta_engine/services/eco_service.py:1`；`wc -l` = 3199 |
| `plm_engineering` | `manufacturing.BOMType` 支持 EBOM/MBOM 切换 | `src/yuantus/meta_engine/manufacturing/models.py` |
| `mrp` | `meta_engine/manufacturing`（1650 行） | — |
| `quality` + `quality_control` | `meta_engine/quality`（973 行） | — |
| `documents` / `mirror_document_server` 多站点部分 | `meta_engine/document_sync`（1732 行 + 12 测试：drift / lineage / reconciliation / retention） | — |
| `approvals` *(core)* | `meta_engine/approvals`（1279 行） | — |
| `activity_validation`（**ECO 活动门控**部分） | `ECOActivityGate` / `ECOActivityGateEvent` + ECOService 在 move/apply 前检查 blockers | `src/yuantus/meta_engine/models/parallel_tasks.py:59`；`src/yuantus/meta_engine/services/eco_service.py:193` (`_ensure_activity_gate_ready`) |

### 3.2 Integrated but incomplete（模型/路由已落，缺运行时闭环或上下游联动）

| Odoo 模块族 | Yuantus 现状 | 仍缺 | 证据 |
|---|---|---|---|
| `mrp_workorder_plm` | 已有 workorder docs 关联端点 + `Operation` 文档字段 | **version-lock**：未把 BOM/Doc 版本钉到具体工单，存在用错图纸/旧 BOM 风险 | `src/yuantus/meta_engine/web/parallel_tasks_workorder_docs_router.py:157`；`src/yuantus/meta_engine/manufacturing/models.py:143` |
| `plm_breakages` + `plm_ent_breakages_helpdesk` | `BreakageIncident` 模型 + `/breakages/*` 路由 + helpdesk sync/status/result/ticket-update | 闭环到 ECO / 设计回流缺；统计/分析报表薄 | `src/yuantus/meta_engine/models/parallel_tasks.py:168`；`src/yuantus/meta_engine/web/parallel_tasks_breakage_router.py:399` |
| `plm_consumption_plans` | `ConsumptionPlan` + `ConsumptionRecord` + `/consumption/plans/{plan_id}/variance` 路由 | 与 MES 实际数据接入、与 quality SPC 聚合面尚未串通 | `src/yuantus/meta_engine/models/parallel_tasks.py:134,156`；`src/yuantus/meta_engine/web/parallel_tasks_consumption_router.py:354` |
| `base_automation` + `plm_workflow_custom_action` | `WorkflowCustomActionRule` + 3 类动作（`emit_event` / `create_job` / `set_eco_priority`），ECO transition 已接入 | 缺 Odoo 式通用 DSL（任意 trigger / 条件表达式 / 任意 service-call）；事件 emit 覆盖面有限 | `src/yuantus/meta_engine/models/parallel_tasks.py:97`；`src/yuantus/meta_engine/services/parallel_tasks_service.py:2005`（`_ALLOWED_TYPES`） |
| `quality_mrp_workorder*` 全家桶 | `QualityPoint` / `QualityCheck` 已有 `routing_id` + `operation_id`；alert 可返回 manufacturing context | **运行时按工序自动触发 / 强制完成**机制缺；worksheet 化缺 | `src/yuantus/meta_engine/quality/models.py:90,93,145`；`src/yuantus/meta_engine/quality/service.py:330` |
| `plm_pack_and_go` | `plugins/yuantus-pack-and-go/` 插件已在仓库 | 是否**主线化** / 与 version-lock 合并 / 是否替换为内置 `bom_archive`——是策略问题，不是从零新建 | `plugins/yuantus-pack-and-go/main.py` |
| `plm_automated_convertion` CAD 转换池 | job-backed conversion router / worker / pipeline 已落地 | 多服务器池 + 按规则分发 + 背压调度策略缺 | `src/yuantus/meta_engine/web/file_conversion_router.py:141`（`_queue_file_conversion_job`、`_build_conversion_job_worker`） |
| `mrp_workorder` | 有 `Operation` / `WorkCenter` 数据面 | Gantt / 调度面 / 实时报工缺 | — |
| `mrp_subcontracting` 子模块（quality / cost） | `meta_engine/subcontracting`（1262 行）覆盖订单与事件 | 未串到外协质量、外协成本归集 | — |
| `documents` 文档管理（完整） | 多站点同步成熟（见 3.1），存储抽象在 `storage` | 文档分类 / 保留策略 / 归档管理薄 | — |
| `attachment_indexation` | search service 存在 | CAD 附件全文索引覆盖度需复核 | — |
| `maintenance` / `maintenance_worksheet` | `meta_engine/maintenance`（638 行，含 schedule） | worksheet 化、预测性维护缺；与 `manufacturing` 未桥接 | — |

### 3.3 Prototype exists（雏形/单点，能力薄）

| Odoo 模块族 | Yuantus 现状 | 备注 |
|---|---|---|
| `activity_validation`（**ECR 入口**部分） | 无独立 ECR domain | ECO 活动门控已在；ECR 受理是真实空缺（见 §四） |
| `approvals_purchase*` | 通用审批已成型（见 3.1） | 未接业务模块（采购/库存等），但 Yuantus 主线 PLM-only 时不必接 |

### 3.4 Absent（仓库内无实现）

| Odoo 模块族 | 判断 |
|---|---|
| `mrp_mps` | 主生产计划 |
| `mrp_account` / `mrp_landed_costs` | 制造成本归集 / 落地成本 |
| `mrp_product_expiry` | 物料保质期（`version.effectivity` 是设计有效期，不同语义） |
| `mrp_workorder_iot` / `quality_iot` / `quality_control_iot` | IoT 采集 |
| `quality_repair` | 质检→返修自动派生 |
| `repair` / `mrp_repair` / `helpdesk_repair` | 售后返修工单链路（与 3.2 中 `BreakageIncident` 互补，下游环节缺） |
| `mrp_maintenance` | 维护↔制造工单桥（取决于 3.2 maintenance 是否先做厚） |
| `barcodes` + GS1 | 条码体系 |
| `product_matrix` | 变体矩阵 / configure-to-order |

### 3.5 Yuantus 比 Odoo 更深的部分（心理基线）

- **CAD 去重 / 相似度**：`meta_engine/dedup`（1184 行 + 6 测试，pHash + 特征匹配 + 阈值规则 + 批处理）—— Odoo 完全没有。
- **多站点文档同步**：`document_sync`（1732 行 + 12 测试：drift / lineage / reconciliation / retention）—— 远超 `plm_document_multi_site` 的简单复制。
- **Version checkout/checkin/merge**：2321 行 + 67 测试 —— 比 Odoo `plm` 的 revision mixin 严格。
- **租户化与可观测性**：Phase 1-3 schema-per-tenant + 熔断 + 审计 —— Odoo addon 模型不具备的平台能力。

---

## 四、按 PLM 价值链断点排序的最大空缺

> **R2 重排原则**：基于 §三 三档分类，把"已有雏形但缺闭环"的项排到前面（性价比高、改造小），把"完全 Absent"放后面。

### 1. PLM ↔ MES 工单 version-lock（最高）
- **对标**：`mrp_workorder_plm`
- **现状**：workorder docs 路由 + `Operation` 文档字段已落地（见 3.2）
- **真实缺口**：BOM/Doc 版本未钉到工单实例，现场仍可能拿到旧版本
- **建议**：在 `parallel_tasks_workorder_docs_router` 上增加 `version_id` 锁定参数 + 在 ECO 发布事件中强制刷新关联工单的版本指针；不需要新域

### 2. ECR 受理入口（高）
- **对标**：`activity_validation`（**入口**部分）
- **现状**：ECO 活动门控（gate + blocker 检查）已在 `eco_service.py:193`；ECO 子任务由 `ECOActivityGate` 承载
- **真实缺口**：没有"变更请求 → 三角化 → 派生 ECO"前端环节
- **建议**：新增 `ChangeRequest` 域（intake → triage → 派生 ECO），复用现有 `ECOActivityGate` 机制串到 ECO

### 3. 质检按工序的运行时强制（高）
- **对标**：`quality_mrp_workorder*`
- **现状**：`QualityPoint` / `QualityCheck` 已有 `routing_id` / `operation_id`（见 3.2）
- **真实缺口**：运行时按工序自动触发检验 + 强制完成 + worksheet 化
- **建议**：在 `Operation` 启动/完成事件上挂 `quality.service` 钩子，未完成检验阻止下一步（默认关闭，feature flag）

### 4. pack-and-go 主线化 / version-lock 强化（中-高）
- **对标**：`plm_pack_and_go`
- **现状**：`plugins/yuantus-pack-and-go/` 已存在
- **真实问题**：是策略选择——是否把插件**主线化**、是否与 §四.1 的 version-lock 合并、是否再独立做 `bom_archive`
- **建议**：先做主线化评估（小 RFC），再决定是否动代码

### 5. CAD 转换池多服务器化（中）
- **对标**：`plm_automated_convertion`
- **现状**：job-backed 单点转换链已落地（`file_conversion_router.py:141`）
- **真实缺口**：多服务器池注册 + 按规则分发 + 背压调度
- **建议**：在现有 conversion job 体系上加 `convert_server` + `convert_rule` 两张表，调度面复用 P6 `CircuitBreaker`

### 6. 自动化规则引擎泛化（中）
- **对标**：`base_automation` + `plm_workflow_custom_action`
- **现状**：`WorkflowCustomActionRule` + 3 类固定动作（`emit_event` / `create_job` / `set_eco_priority`）已接入 ECO transition（见 3.2）
- **真实缺口**：动作类型固定（白名单 3 个），无通用 DSL；事件 emit 覆盖面有限
- **建议**：先扩 emit 事件覆盖（lifecycle / approvals / version 三大状态机），再考虑 DSL 是否值得

### 7. breakage → 设计回流闭环（中）
- **对标**：`plm_breakages` 下游 + `repair` / `helpdesk_repair`
- **现状**：`BreakageIncident` 数据面 + helpdesk 联动已在（见 3.2）
- **真实缺口**：未自动派生 ECO / 设计回流；缺统计分析报表
- **建议**：在 `BreakageIncident` 状态机上加"派生 ECO"动作，复用 §四.2 的 ChangeRequest 域

### 8. consumption_plan ↔ MES 数据接入（中）
- **对标**：`plm_consumption_plans`
- **现状**：`ConsumptionPlan` / `ConsumptionRecord` + `/variance` 已在（见 3.2）
- **真实缺口**：MES 实际数据回填路径未接通、与 quality SPC 聚合面缺
- **建议**：先定义"MES → ConsumptionRecord"摄取契约（contract test only），再决定接入方式

### 9. 设备保养 ↔ 工单（中-低）
- **对标**：`mrp_maintenance`
- **现状**：`maintenance` 域薄（638 行 + schedule）
- **建议**：先把 `maintenance` 做厚（worksheet / 预测维护），再补 mrp 桥

### 10. MPS / 主生产计划（中-低）
- **对标**：`mrp_mps`
- **判断**：Yuantus PLM-only 定位下可暂不做；若客户要"研发→生产→排产"一体化则必须补

### 11. 变体矩阵 / configure-to-order（低）
- **对标**：`product_matrix`
- **判断**：BOM 变体场景才需要

### 12. 条码体系（低）
- **对标**：`barcodes` + GS1
- **判断**：仓储 / MES 场景才需要

### 13. 审批接业务（低）
- **对标**：`approvals_purchase*`
- **判断**：业务采购入站后才需要

---

## 五、落地建议

**纪律前提**：每一项独立 opt-in，独立 PR，独立 taskbook；不打包；默认关闭；强测试；不迁移现有数据。

**R2 重排建议优先序**（"现有代码下最合理的下一步"——优先做"已有雏形 → 补闭环"而非"从零新增"）：

| 序 | 工作项 | 类型 | 价值 | 工作量 | 关键依赖 |
|---|---|---|---|---|---|
| 1 | workorder version-lock | 补闭环 | 高 | 小-中 | `parallel_tasks_workorder_docs_router` + ECO 发布事件 |
| 2 | ECR intake domain | 新建 | 高 | 中 | 复用 `ECOActivityGate` |
| 3 | 质检按工序运行时强制 | 补闭环 | 高 | 中 | `Operation` 启停事件 + `quality.service` |
| 4 | pack-and-go 主线化评估 + version-lock 强化 | 策略 RFC + 小 PR | 中-高 | 小 | `plugins/yuantus-pack-and-go/` |
| 5 | CAD 转换池多服务器化 | 补闭环 | 中 | 中 | `file_conversion_router` + P6 `CircuitBreaker` |
| 6 | 自动化规则引擎泛化（先扩事件 emit） | 补闭环 | 中-高 | 中-大 | lifecycle / approvals / version 状态机 |
| 7 | breakage → 设计回流闭环 | 补闭环 | 中 | 中 | `BreakageIncident` 状态机 + ECR domain |
| 8 | consumption_plan ↔ MES 摄取契约 | contract first | 中 | 小（契约） | `ConsumptionRecord` |
| 9 | 维护↔工单桥（先做厚 maintenance） | 厚薄域 | 中-低 | 小-中 | `maintenance` |

**与现有 Phase 进度的对齐**：

- Phase 3 cutover 仍按 5 项 stop-gate 等外部输入；本文不预设其落地时间。
- Phase 5 / 6.3 / 6.4 已有独立 opt-in 通道；本文新建议不与之合并。
- 上述 9 项均为新 Phase 候选，需要独立项目级 opt-in 后才能拆 taskbook。

**正式入库建议**：本文与 `DELIVERY_DOC_INDEX.md` 索引条目已落地；R2 修订完成后还需运行 doc-index trio（如项目约定）做一致性校验，再视情况发 cycle PR。

---

## 附：本次调研未覆盖（避免范围漂移）

- **不在本文范围**：定价 / 合同 / 销售流程（Odoo `sale*` 系列）、HR / 考勤 / 薪酬、财务报表、电商 / POS、CRM / 营销自动化。这些虽然在 Odoo 内与 PLM 通过 `product` 主数据弱关联，但与 Yuantus 当前 PLM-only 定位无关。
- **不重新论证**：`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` 中已列出的"主线内可落地的能力补齐" 12 项。本文为其扩展补充，不重述。

---

**作者**：Claude（基于 2026-05-14 codebase 快照）
**复核**：待人工签核
**关联文档**：`DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md`、`DESIGN_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md`、`ARAS_PARITY_SCORECARD.md`
