# Yuantus PLM × Odoo18 PLM 能力差距与优化建议（20260420）

> **范围**：本文基于对 `src/yuantus/` 主干（含 `meta_engine`、`integrations`、`security`、`api/routers`）与 `references/odoo18-enterprise-main/addons/` 下 37 个 PLM addon 的对照阅读，并已对齐 `docs/DEVELOPMENT_STRATEGY_PARITY_TO_SURPASS_20260321.md` / `DEVELOPMENT_PLAN.md` 中声明的「不做横向扩张，主线锁死在 **Part / BOM / Rev / ECO / Doc / CAD**」纪律。
>
> **结构**：
> - 一、**主线内可落地的能力补齐**（建议优先执行）
> - 二、**架构与工程优化热点**（与功能开发并行推进）
> - 三、**已识别但按纪律暂缓**（避免重复讨论）
> - 四、**落地建议：三件最应先推的事**

---

## 一、主线内可落地的能力补齐（优先）

这部分是 Odoo 已有、Yuantus 仍欠缺或只做到一半、**且符合团队已声明主线范围**的能力。

### 1. 自动部件编号 / 内部编码（对标 `plm_auto_engcode` + `plm_auto_internalref`）

- **证据**：在 `src/yuantus/` 全库 grep `ir_sequence | auto_sequence | NumberingRule | SequenceService | auto_generate_code` **零命中**；`seeder/prod/standard_parts.py` 只有示例种子数据，没有按 ItemType / Category 下发序列号的服务。
- **建议**：新增 `meta_engine/services/numbering_service.py`：
  - 按 `ItemType` / Category 配置 `sequence_pattern`（前缀、位数、起始、重置周期、是否按年重置）。
  - Item 新建时在 `AMLEngine.add` 路径里自动下发，UI 只读。
  - 附带把 `seeder/prod/standard_parts.py` 当前的手工部件号标准化。
- **价值**：工程出件极高频动作，当前全靠手填，风险面覆盖撞号、审计缺失、跨 tenant 命名混乱。

### 2. 「仅最新已发布版本」下游约束（对标 `plm_product_only_latest / _purchase / _sale`）

- **证据**：`meta_engine/services/bom_obsolete_service.py` 中的 `BOMObsoleteService.scan()` 只做**事后扫描**（检测到哪些 BOM 行已过期）。在 BOM 新增、子项替换、采购/销售等消费入口**没有做准入拦截**。
- **建议**：
  - 在 `effectivity_service.py` / `substitute_service.py` / `bom_service.py` 入口增加 `require_latest_released_only=True` 策略开关。
  - 对 `meta_engine/web/bom_router.py` 的新增/替换子项端点挂 guard，复用 `lifecycle/guard.py` 状态判定。
  - 对外对接合同（`contracts/`）应保留「降级」模式，但默认启用强校验。
- **价值**：堵住「图纸已发布但领料 / 采购 / 工单还在用旧版」这一质量高发路径，Odoo 三件套是企业最常激活的 addon 之一。

### 3. Suspended（挂起）生命周期态（对标 `plm_suspended`）

- **证据**：`seeder/meta/lifecycles.py` 仅定义 Draft → Released → Obsolete；`lifecycle/` 目录下 grep `suspend(ed)?` **零命中**。
- **建议**：在 `lifecycle/models.py` 扩一个**可租户开关**的中间态（Suspended）；BOM / 采购 / 工单端在该态一律 block。
- **价值**：工程暂停复核场景的标配——出问题的零件不能直接作废，也不能继续消费。

### 4. ECO 多级会签 + 活动到期升级（对标 `activity_validation` + `plm_workflow_custom_action`）

- **现状**：
  - `approvals/` + `workflow/service.py` 已有 `ApprovalRequest` / `WorkflowActivity` / `WorkflowTask` / `ApprovalCategory` 模型。
  - 但调研结论明确标注**审批升级 / 权重表决 / 并行表决 / 通知触达均 stub**。
- **建议**：
  ① `workbench.html` 的 Workflow Designer 补齐「并行表决模板」 + 「标准三级门（设计→工程→质量）」 + 「活动模板包」。
  ② 用二.2 的调度器扫描超期 activity 自动升级 / 转派。
  ③ 把 `ApprovalCategory` 与 ItemType 绑定，支持按 Item 类型切换审批矩阵。
- **价值**：已列入 `DESIGN_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md` 的 bounded increment 候选，正好续上 Lane B。

### 5. BOM→MBOM 自动化 + 日期生效调度（对标 `plm_automate_normal_bom` + `plm_date_bom`）

- **现状**：
  - `manufacturing/mbom_service.py` 存在但只做静态 release。
  - `effectivity_service.py` 已有 `effectivity_from/to` 字段，但没有调度器按日切换当前生效版。
- **建议**：
  - ECO `Released` 事件通过现有 `events/event_bus.py` 触发 `mbom_service.sync_from_ebom()`。
  - 用二.2 的调度器每日扫描到期行并切换生效指针。
  - 记入 Outbox 表保证事件不丢（见二.1）。
- **价值**：工程-制造手动同步 → 自动同步，是 Odoo 最常用的 PLM 流程自动化。

### 6. BOM 去重汇总 + 产品描述多语言（对标 `plm_bom_summarize` + `plm_product_description_language_helper`）

- **现状**：
  - `bom_service.py` 已支持 `only_product / summarized / by_item / detailed / full` 多种 compare 模式，但**上传/导入流程不做行合并**。
  - `locale/` 仅到租户级语言，没有属性级多语言字段。
- **建议**：
  - `cad_bom_import_service.py` commit 前按 `(item_id, UoM)` 聚合重复行，聚合规则可配置（求和 / 平均 / 保留首行）。
  - Item `properties` 增加 `{lang: value}` 多语言字符串 helper，配合 `locale_router.py` 的 lang 参数返回解析后的字段。
- **价值**：中 / 日 / 德 OEM 客户常见诉求。

### 已确认 Yuantus 已有、不用重复提

| 能力 | 对应 Odoo | Yuantus 实现位置 |
|---|---|---|
| BOM 重量 rollup | `plm_automatic_weight` | `meta_engine/services/bom_rollup_service.py`（`compute_weight_rollup`） |
| Obsolete 扫描 | 部分 `plm_suspended` | `meta_engine/services/bom_obsolete_service.py` |
| Config 条件 | `plm_date_bom` 部分 | `meta_engine/lifecycle/condition_evaluator.py` + Item `config_condition` |
| 等效件 / 替代件 | `plm_spare` 部分 | `equivalent_service.py` + `substitute_service.py` |
| 切割件 | `plm_cutted_parts` | `meta_engine/cutted_parts/` |
| 非 CAD 档案盒 | `plm_box` | `meta_engine/box/` |
| 文档多站点同步（基础面） | `plm_document_multi_site` | `meta_engine/document_sync/` |
| 电子签名 | — | `meta_engine/esign/` |
| BOM 比较（后端） | `plm_compare_bom`（后端） | `meta_engine/services/bom_service.py` |
| CAD 查看（基础） | `plm_web_3d`（基础） | `meta_engine/web/cad_router.py` + `web/cad_preview.html` |

---

## 二、架构与工程优化热点（与功能并行推进）

下列全部基于 Yuantus 代码**行数 + 耦合观察**，非主观评价。

### 2.1 单文件巨石化 / 复制粘贴热点

| 热点文件 | 规模 | 问题 | 建议 |
|---|---|---|---|
| `meta_engine/web/parallel_tasks_router.py` | 4202 LOC | breakage / CAD conversion / dedup 三类 task 挤在一起 | 按 task type 拆成独立 router，抽 `TaskRunner` 基类 |
| `meta_engine/web/subcontracting_governance_row_discoverability.py` | 3785 LOC | 过滤 / 排序 / 分页手搓，与 `subcontracting_consumer_row_discoverability.py` (813 LOC) 大量重复 | 抽 `DiscoverabilityQueryBuilder` 基类，两端复用 |
| `meta_engine/web/cad_router.py` | 2386 LOC | 上传 / 预览 / manifest / import 杂糅 | 拆 `cad_upload` / `cad_preview` / `cad_manifest` 三个 router |
| `meta_engine/web/bom_router.py` | 2127 LOC | explode / compare / where-used / import 全写在 handler 里 | compare / explode 逻辑下沉到 `bom_service`；router 只做 HTTP |
| `meta_engine/web/file_router.py` | 1982 LOC | upload / convert / preview / asset 合并 | 按职责切成三个 router |
| `meta_engine/web/eco_router.py` | 1417 LOC | 业务逻辑和 HTTP 强耦合 | 全部委托 `ECOService`，router 只做校验 |
| `api/routers/admin.py` | 1100+ LOC | tenant / user / quota / audit 全堆 | 拆成 `admin_tenant_router` / `admin_user_router` / `admin_quota_router` / `admin_audit_router` |

### 2.2 跨模块重复 / 双份声明

| 现象 | 建议 |
|---|---|
| `integrations/{athena, cad_connector, cad_extractor, cad_ml, dedup_vision}.py` 5 份并行 client，`auth / retry / timeout` 逻辑各自复制 | 基于 `integrations/http.py` 抽 `BaseIntegrationClient`，五个 client 继承，统一 headers、重试、熔断、超时 |
| `security/rbac/permissions.py` 与 `meta_engine/permission/models.py` 两处都在声明权限表 | 合并为单一 `PermissionRegistry`；从 router decorator 扫描 permission 声明，避免漏同步 |
| `meta_engine/services/engine.py`（AMLEngine）中心化，`import` 链易循环 | 按 op 拆 `AddEngine / UpdateEngine / DeleteEngine / PromoteEngine`；公共部分抽到 `engine_base.py` |

### 2.3 两项系统级优化

#### 2.3.1 事件总线持久化

- **现状**：`events/event_bus.py` 当前是**内存发布**，进程重启即丢；`events/transactional.py` 的 deferred event 是 session-scoped。
- **建议**：
  - 新增 `outbox` 表（Item 变更、ECO 状态迁移、文件转换完成等领域事件落库）。
  - 选一个轻量通道：Postgres `LISTEN/NOTIFY` 最小侵入；Redis Streams 更利于扩 worker。
  - 配合 Lane C 的 strict-gate / perf evidence，事件丢失率直接是 KPI。

#### 2.3.2 轻量调度器

- **现状**：Yuantus 调研报告明确标注「No cron / scheduled jobs」。
- **建议**：落一个 `scheduler_service`（APScheduler 级别即可），一次性解锁：
  - 一.4 审批超期自动升级
  - 一.5 MBOM 自动同步 + effectivity 按日切换
  - 审计日志 retention（`security/audit_retention.py` 当前是手动触发）
  - 报表汇总 / 统计快照

---

## 三、已识别但按纪律暂缓（仅登记，避免重复讨论）

| Odoo 模块 | 映射能力 | 暂缓原因 |
|---|---|---|
| `plm_pdf_workorder(_enterprise)` | 工单文档下沉到车间 | 需要 MES / 执行层，超出主线 |
| `plm_breakages` + `plm_ent_breakages_helpdesk` | 残次品 + Helpdesk 联动 | Yuantus 已有 `breakage_tasks`；helpdesk 联动属横向扩张 |
| `plm_consumption_plans` | 消耗计划 | 依赖 MES 消耗数据源 |
| `plm_spare` | 备件手册生成 | 与售后管理耦合 |
| `plm_project` | 工程项目联动 | 不接项目管理 |
| `plm_pack_and_go` | ZIP 导出 | `plugins/yuantus-pack-and-go` 已实现为插件，先与 `file_router` 合并后再考虑主线化 |
| `plm_document_multi_site` | 多站点文档镜像 | `document_sync` 主干已有；冲突解决 / 断线续传属运维增强 |
| `plm_web_3d` / `_sale` | 3D 在线浏览 / Sale 侧 | 查看器专项，等 Lane A 的 `/cad/capabilities` 合同收敛后再推 |
| `plm_auto_translator` / `plm_report_language_helper` | 自动翻译 / 报表选语言 | 先做 §一.6 的产品描述多语言 helper，报表层暂缓 |
| `plm_compare_bom` 独立 wizard UI | `bom_service` 已有 compare 逻辑，仅差 UI | 视 workbench 排期 |
| `plm_client_customprocedure` | 角色程序组 | Yuantus RBAC 已覆盖基础面，procedure group 纯 Odoo 风格，非必要 |

---

## 四、落地建议：三件最应先推的事

按 **ROI × 主线对齐度** 排序：

1. **一.1 + 一.2 合并为一个 bounded increment**（自动编码 + 仅最新已发布版本）
   - 工程出件质量收益最大
   - 符合 Lane B「下一轮 Odoo18 对标」节拍
   - 建议同步更新 `contracts/` 合同文档

2. **二.1 的两个巨石 router 拆分**（`parallel_tasks_router.py` 4202 LOC + `subcontracting_governance_row_discoverability.py` 3785 LOC）
   - 已到拖累 review / 覆盖率的临界点
   - 收益可量化（PR review 时长、单测覆盖率、导入时间）
   - 可在同一个 bounded increment 内完成，不受功能冻结影响

3. **二.3 调度器**（轻量 APScheduler + outbox 表）
   - 一次性解锁 §一.4（审批超期）、§一.5（MBOM / effectivity）、审计 retention、报表汇总 四条依赖链
   - 为 Lane C 的 strict-gate / perf evidence 提供新的可测量指标

---

## 参考文件

- `docs/DEVELOPMENT_PLAN.md`
- `docs/DEVELOPMENT_STRATEGY_PARITY_TO_SURPASS_20260321.md`
- `docs/DELIVERY_PLAN_PARITY_TO_SURPASS_20260321.md`
- `docs/DESIGN_PARALLEL_ODOO18_REFERENCE_PARITY_FINAL_SUMMARY_20260407.md`
- `docs/ODOO18_REFERENCE_PARITY_READING_GUIDE_20260407.md`
- `docs/ARAS_PARITY_SCORECARD.md`
- `references/odoo18-enterprise-main/addons/`（37 个 PLM addon）
- `src/yuantus/meta_engine/`（Yuantus 主干实现）
