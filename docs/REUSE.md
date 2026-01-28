# PLM/src 代码复用说明（迁移到 YuantusPLM / 元图PLM）

本文档说明 `/Users/huazhou/Downloads/Github/PLM/src` 目录下的代码，哪些**适合直接复用**、哪些**建议抽象后复用**、哪些**只建议参考**，以及迁移到当前仓库（`yuantus-plm`）的推荐路线。

> 目标：复用“高价值、低耦合”的核心能力（Meta Engine、版本、权限、文件、变更等），避免把旧工程的耦合与历史包袱整体搬过来。

---

## 总览（按复用价值分层）

| PLM/src 子目录 | 体量（参考） | 复用建议 | 原因（摘要） |
|---|---:|---|---|
| `plm_core/` | ~3.1M | ✅优先复用 | 领域模型与核心服务集中，迁移收益最高 |
| `plm_api/` | ~1.2M | 🟡选择性复用 | 路由/依赖/鉴权中有可取模式，但 API 形态需按 Yuantus 统一 |
| `plm_framework/` | ~3.1M | 🟡按模块抽取 | 横切能力多，但“框架化”容易引入耦合；建议“摘果子” |
| `odoo_compat/` | ~500K | 🟡作为参考/按需抽取 | 与 Odoo/转换器思路相关，通常要适配新存储与任务系统 |
| `plm_enhanced/` | ~376K | 🟡仅参考/择优摘取 | 以“单文件功能块”形式给出增强实现，可当作设计输入 |
| `plm_extensions/` | ~20K | 🟡参考后迁移 | hook/扩展点示例（如自动编号、审计日志），适合迁移为 Yuantus 插件/钩子 |
| `plugins/` | ~40K | 🟡仅参考 | 基于旧 `plm_framework` 的插件示例，可借鉴契约/事件分层，但不建议直接搬实现 |
| `plm_modules/` | ~184K | ❌不建议直接复用 | 偏业务插件/历史实验性模块，建议按需重写为 Yuantus 插件 |
| `plm_odoo_integration/` | ~204K | ❌不建议直接复用 | Odoo 强耦合，除非明确做 Odoo 集成再单独迁移 |
| `scripts/` | ~12K | ❌不建议直接复用 | 多为初始化脚本（偏 Odoo/旧权限模型），只作参考 |
| `dedup2_service/` | ~8K | 🟡仅参考 | 早期去重服务骨架；当前更建议对接 `dedupcad-vision` |
| `web_client/` | ~145M | ❌不建议直接复用 | node_modules/构建体系/技术债重；建议重做或仅参考 UI 交互 |

> 说明：`plm.db` / `plm_dev.db` / `*.db-wal` 等为旧工程的 sqlite 数据文件，不建议作为“代码复用”内容迁移；如需迁移数据，建议走导入/映射脚本路线。

---

## 关系模型现状（重要）

- 关系事实源：`meta_items`（`ItemType.is_relationship=true`）。  
- `meta_relationships` / `RelationshipType` 已废弃，仅保留只读兼容与统计。  
- 新开发 **不允许** 直接写入 `meta_relationships`；统一走 ItemType 关系与 `Item` 关系行。  
- 管理端 legacy 统计/告警见：`/api/v1/admin/relationship-writes` 与 `relationship-types/legacy-usage`。  

> 备注：这意味着旧工程中基于 `RelationshipType` 的写入逻辑不应直接迁入；应改为“关系即 Item”的统一路径。

---

## 1) 可直接复用（建议“拷贝 + 对齐 import + 补测试/文档”）

### 1.1 Meta Engine（核心）

**推荐来源：**
- `PLM/src/plm_core/meta_engine/*`

**迁移目标：**
- `src/yuantus/meta_engine/*`

**适合直接复用的内容：**
- 元模型：`models/`（Item/ItemType/Property/Relationship 等）
- AML/操作：`operations/`、`parsers/`
- 生命周期：`lifecycle/`
- 权限：`permission/`
- 版本：`version/`
- 视图：`views/`（表单/列表配置的元数据）
- 服务层：`services/`（注意见下文 ECO/变更）

**迁移注意点：**
- 统一多租户/多组织上下文：Yuantus 已采用 `x-tenant-id`/`x-org-id`（ContextVar），迁移时避免引入旧工程的全局单例。
- 把“路由层/依赖注入/权限校验”留在 Yuantus（`src/yuantus/api`），Meta Engine 尽量保持纯业务/可测试。

### 1.2 租户上下文模型（概念可复用）

**推荐来源：**
- `PLM/src/plm_core/tenant/tenant_context.py`
- `PLM/src/plm_core/tenant/tenant_manager.py`

**怎么用：**
- `tenant_context.py` 的 ContextVar 思路已在 Yuantus 中使用（tenant/org 双上下文）。
- `tenant_manager.py` 的 `TenantPlan/Limits/Usage` 很适合做后续 SaaS 的“套餐/配额/计费”模型，可直接迁移到 `src/yuantus/tenancy/`（建议后续实现为 DB 持久化而不是内存对象）。

### 1.3 插件系统（可作为“模块化/微服务化”的落地）

**推荐来源：**
- `PLM/src/plm_core/plugin_manager/*`

**复用价值：**
- 支持“可插拔模块/连接器/转换器”，适合 CAD 对接、导入导出、规则引擎等扩展点。

**迁移方式（建议）：**
- 先把插件管理器迁移为 `src/yuantus/plugin_manager/`（保持纯 Python，不依赖 FastAPI）。
- Yuantus API/Worker 通过插件注册扩展路由、任务、字段类型、转换器能力（逐步引入，不要一次性把所有 hooks 打开）。

---

## 2) 选择性复用（建议“抽象接口 → 迁移实现 → 统一配置/日志/错误码”）

### 2.1 ECO/变更（强建议复用，但要“一对一对齐 router/service”）

**推荐来源：**
- `PLM/src/plm_core/meta_engine/services/eco_service.py`
- `PLM/src/plm_core/meta_engine/services/change_service.py`
- 相关测试：`PLM/src/plm_core/meta_engine/tests/test_change_service.py`

**为什么要谨慎：**
- ECO 是跨模块能力（版本/权限/BOM/工作流/通知），最容易在迁移中出现“路由调用的方法不存在”的问题。

**推荐做法：**
- 先决定 Yuantus 的 ECO API 合同（REST/RPC 都可），再把 PLM 的 `eco_service/change_service` 迁移进来；
- 迁移时保持 **router 与 service 版本一致**：要么一起迁移，要么先不挂载该路由，避免 500。

### 2.2 去重/相似检索（对接 dedupcad-vision 的契约）

**推荐来源：**
- `PLM/src/plm_core/dedup/interfaces.py`（接口契约）

**怎么复用：**
- 保留接口契约（ContextProvider/StorageProvider/IndexProvider），在 Yuantus 中实现“HTTP provider”对接 `dedupcad-vision`；
- 把“算法/向量索引实现”放在 dedup 服务侧，Yuantus 侧只保留契约与编排（触发、回写、权限范围）。

**身份透传（报告归档/权限）**
- 对接 dedupcad-vision 时建议透传 `x-user-id`（或 `Authorization` JWT 的 `sub`）。
- Yuantus 的 `build_outbound_headers()` 已包含 `x-user-id`，可直接复用，无需额外改造。

### 2.3 API 中间件（限流/CSRF 等）

**推荐来源：**
- `PLM/src/plm_api/middleware/*`

**复用建议：**
- SaaS 场景建议复用“限流”思想，但实现要融入 Yuantus 的鉴权与 tenant/org 维度（例如按 tenant 限流、按 org 配额）。

### 2.4 plm_framework（以“能力清单”方式摘取）

`plm_framework/` 中很多模块适合做“参考实现/未来规划”，但不建议整体搬迁。

优先可摘取的方向：
- `search/`：查询 DSL、索引抽象（与 OpenSearch/ES 或 pg_trgm/pgvector 的适配）
- `events/`：领域事件模型（Outbox + 消息总线的形态）
- `workflow/`：工作流状态机/审批模式（与 ECO/变更密切相关）
- `integration/`：对外集成的 adapter 模式（CAD/ERP/MES）

---

## 3) 不建议直接复用（建议“只读参考”）

- `web_client/`：构建体系重、node_modules 体积大；建议后续单独仓库、单独前端栈重做（React/Vue 均可），或仅复用页面布局/交互思路。
- `plm_odoo_integration/`、`odoo_compat/frontend/`：除非明确要对接 Odoo，否则建议先不要迁移，避免引入 Odoo 生态耦合。
- `plm_modules/`：偏业务插件（条码、图片、有效期等），与机械行业 PLM 关联较弱，建议后续按需再做。

---

## 4) 推荐迁移路线（从“可验证”出发）

1) **先稳定内核**：Meta Schema + AML + BOM + File + Version + RBAC（每一步都加验证命令/文档）。
2) **再打通变更**：ECO/Change（先最小闭环：创建 ECO → 影响分析 → apply → 版本/记录落库）。
3) **再上 CAD 对接**：把 CAD 连接器做成插件或独立微服务（Worker/Queue），核心服务只做“任务编排 + 权限 + 追溯”。
4) **再做 SaaS 维度**：Tenant/Org/User/Role/Quota 落库；把限流/配额、存储隔离、审计、计费接入。

---

## 5) 对 YuantusPLM 的落地建议（一句话）

从 `plm_core/meta_engine` 复用“内核”，从 `plm_core/plugin_manager` 复用“扩展机制”，其余框架化代码只“按需摘取”，这样最利于后续做模块化/微服务化与长期维护。

---

## 6) 当前迁移状态（本仓库 `yuantus-plm`）

- ✅ 已迁移并可验证：Meta Engine 基础（AML/Meta/BOM）、文件上传/挂载、版本初始化/历史/树、多租户/多组织（dev 模式 db-per-tenant/db-per-tenant-org），详见 `docs/VERIFICATION.md`
- ✅ CAD 导入任务编排（MVP）：`POST /api/v1/cad/import` 创建 `cad_preview` 等后台任务；Worker 执行后可通过 `GET /api/v1/file/{file_id}/preview` 获取预览（占位图/真实预览取决于依赖）
- ⚠️ ECO/Change：建议以 `PLM/src/plm_core/meta_engine/services/eco_service.py` + `change_service.py` 为准“一对一对齐”迁移；在完成前不建议对外承诺接口稳定性
- ✅ 插件系统（MVP）：已在本仓库落地基础 Plugin Manager，并提供示例插件与插件列表接口（见 `docs/VERIFICATION.md` 的 Plugins 章节）

---

## 7) `PLM/` 仓库（非 `src/`）也有大量可借鉴资产

下面这些内容虽然不在 `PLM/src`，但对“工程化、交付、CAD 集成与质量保障”非常有价值，建议**直接拿来做 Yuantus 的参考实现/规范来源**。

### 7.1 架构与 ADR（可以当作 Yuantus 的设计输入）

- 架构愿景/边界划分：`/Users/huazhou/Downloads/Github/PLM/ARCHITECTURE_VISION.md`
- CAD 集成指导：`/Users/huazhou/Downloads/Github/PLM/CAD_INTEGRATION_GUIDE.md`
- 端口/部署约束：`/Users/huazhou/Downloads/Github/PLM/PORTS.md`
- 大量工程报告/复盘文档：`/Users/huazhou/Downloads/Github/PLM/docs/`

建议用法：
- 把这些文档当作“需求与约束集合”，逐条映射到 Yuantus 的 Roadmap/ADR（不要照搬实现细节）。

### 7.2 测试体系（强烈建议借鉴）

- 测试目录：`/Users/huazhou/Downloads/Github/PLM/tests/`
  - 覆盖范围很广：ECO、BOM、附件安全、权限策略、OpenAPI 合同、迁移链完整性、指标/可观测等。
- Makefile 中有“按功能开关拆分测试会话”的经验：`/Users/huazhou/Downloads/Github/PLM/Makefile`

建议用法：
- 不需要把所有测试迁过来，但可以把它们当作“验收清单”：
  - 先挑 Yuantus 已有的能力（file/version/eco/bom）对应的关键用例，改写为 Yuantus 的 pytest/契约测试。

### 7.3 迁移/数据库运维（可直接借鉴流程）

- Alembic 运维手册：`/Users/huazhou/Downloads/Github/PLM/RUNBOOK_MIGRATIONS.md`
- Alembic 配置与版本链：`/Users/huazhou/Downloads/Github/PLM/alembic.ini`、`/Users/huazhou/Downloads/Github/PLM/alembic/`

建议用法：
- Yuantus 现在是 dev 期 `create_all()`，但进入生产就必须落到 migrations；PLM 的 runbook 可以作为模板。

### 7.4 CAD 客户端与 CAD 插件（可复用“接口合同/交互形态”）

- CAD 插件（示例）：
  - AutoCAD LISP：`/Users/huazhou/Downloads/Github/PLM/tauri-plm-client/cad-plugins/autocad/PLMCommands.lsp`
  - ZWCAD LISP：`/Users/huazhou/Downloads/Github/PLM/tauri-plm-client/cad-plugins/zwcad/PLMCommands.lsp`
  - Plant3D LISP：`/Users/huazhou/Downloads/Github/PLM/tauri-plm-client/cad-plugins/plant3d/PLMPlant3DCommands.lsp`
  - SolidWorks Add-in：`/Users/huazhou/Downloads/Github/PLM/tauri-plm-client/cad-plugins/solidworks/PLMSolidWorksAddin.cs`
- 这些插件的核心模式是：CAD 内只负责触发命令 → 调用本地 `PLMClient.exe` → 再由客户端与服务端交互。

建议用法（对 Yuantus）：
- 先定义 `yuantus-client`（或继续用 `yuantus` CLI 的子命令）作为 CAD 侧统一入口，然后逐步适配这些 CAD 插件把 `PLMClient.exe` 替换为 `yuantus-client`。

### 7.5 异步任务/CAD 转换（可借鉴 Celery 分层）

- Celery app：`/Users/huazhou/Downloads/Github/PLM/app/core/celery_app.py`
- CAD 转换批处理任务：`/Users/huazhou/Downloads/Github/PLM/app/tasks/cad_conversion.py`

建议用法：
- Yuantus 后续做 CAD 转换/大文件预览时，可复用“队列分区（cad/eco/bom/files）+ 定时任务”思路；
- 具体实现可以继续用 Celery，也可以换成你更偏好的 worker（RQ/Arq/Dramatiq），但“任务编排结构”值得保留。

### 7.6 部署与运维样板（可当作私有化交付参考）

- Docker Compose：`/Users/huazhou/Downloads/Github/PLM/docker-compose*.yml`
- K8s/网关：`/Users/huazhou/Downloads/Github/PLM/k8s/`、`/Users/huazhou/Downloads/Github/PLM/nginx/`、`/Users/huazhou/Downloads/Github/PLM/haproxy/`

---

## 8) `references/` 目录参考清单（仅借鉴思路/流程，禁止代码复用）

`/Users/huazhou/Downloads/Github/Yuantus/references` 目录内包含多个成熟系统源码，但许可证约束非常严格。
**建议仅参考“概念/流程/架构”，不要直接复制任何代码/脚本/资源文件。**

### 8.1 许可证提示（务必遵守）

| 来源 | 许可证 | 结论 |
|---|---|---|
| `docdoku-plm` | AGPLv3 | **只做设计参考**（网络服务触发开源义务，禁止代码复用） |
| `erpnext` | GPLv3 | **只做设计参考**（强 copyleft，禁止代码复用） |
| `odoo18-enterprise-main` | LGPLv3 + OEEL（企业模块） | **只做概念参考**（企业模块为专有许可，禁止代码复用） |

### 8.2 允许借鉴的范围（合规做法）

- 业务概念与流程：BOM/Where-Used/BOM Compare/ECO/版本语义/工艺流程
- 数据模型思路：字段选择、层级结构、状态机设计
- API 设计思路：输入/输出、分页/过滤、异常码
- 工程化方式：模块拆分、任务编排、异步处理思路

### 8.3 禁止复用的内容

- 任何源代码、脚本、配置文件、数据库迁移、前端资源
- 任何“只改名/改变量”的形式化复制
- 任何带有许可证头的文件片段

### 8.4 推荐借鉴主题（高价值、低风险）

**DocDoku-PLM（AGPL）**
- 变更流程与生命周期状态机的组织方式
- CAD 转换/预览的“异步任务”分层
- BOM 结构与版本的分离思路

**ERPNext（GPL）**
- BOM 结构的“展开/对比/Where-Used”用例拆分
- 变更与工艺（制造）流程的最小闭环
- 物料与版本管理的字段组织

**Odoo Enterprise（LGPL + OEEL）**
- UI/流程交互的组织方式（只看流程，不看实现）
- BOM/工艺/变更的流程拆解
- 权限与角色模型的层级关系

> 结论：**一律“看思路，自己实现”。** 如需更深度参考，请先确认许可与合规策略。

---

## 9) BOM Compare 字段级对照清单（参考实现用）

本节是 **BOM Compare 的字段级对照清单**，用于指导 Yuantus 实现差异计算。
**仅用于设计/实现参考，不涉及任何第三方代码复用。**

### 9.1 比较范围（推荐）

1. **结构差异（必须）**
   - 关系“存在/不存在”的差异（Added / Removed）
2. **BOM 行属性差异（必须）**
   - 数量/单位/位号/序号/效期等
3. **子件属性差异（可选）**
   - `item_number`、`name`、`state` 等（默认关闭，避免噪音）

### 9.2 关系身份键（核心）

建议比较 Key 优先使用 **稳定身份**，避免版本变更导致“同一零件被误判为新增/删除”。

| 字段 | 来源 | 用途 | 比较规则 |
|---|---|---|---|
| `parent_config_id` | `meta_items.config_id` | 父件稳定身份 | 优先作为 parent key |
| `child_config_id` | `meta_items.config_id` | 子件稳定身份 | 优先作为 child key |
| `parent_id` | `meta_items.id` | 父件实例 | 兜底 |
| `child_id` | `meta_items.id` | 子件实例 | 兜底 |
| `item_type_id` | `meta_items.item_type_id` | 关系类型 | 通常固定 `Part BOM` |

**Key 组合建议**：`parent_key + "::" + child_key`  
- `parent_key` 优先 `parent_config_id`，否则 `parent_id`  
- `child_key` 优先 `child_config_id`，否则 `child_id`

#### Line Key（对齐策略）

| `line_key` | 组成 | 适用场景 | 说明 |
|---|---|---|---|
| `child_config` | `parent_config_id + child_config_id` | 默认 | 一条子件只有一行 |
| `child_id` | `parent_id + child_id` | 版本对齐 | 忽略 config 变化 |
| `relationship_id` | `relationship_id` | 精确对齐 | 仅同一 BOM 行 |
| `child_config_find_num` | `child_config_id + find_num` | 版本对齐 + 序号 | 同一子件多行 |
| `child_config_refdes` | `child_config_id + refdes` | 版本对齐 + 位号 | 同一子件多行 |
| `child_config_find_refdes` | `child_config_id + find_num + refdes` | 版本对齐 + 组合区分 | find_num/refdes 组合 |
| `child_config_find_num_qty` | `child_config_id + find_num + quantity` | 版本对齐 + 数量 | 数量变化视为新增/删除 |
| `child_id_find_num` | `child_id + find_num` | 序号区分 | 同一子件多行 |
| `child_id_refdes` | `child_id + refdes` | 位号区分 | 同一子件多行 |
| `child_id_find_refdes` | `child_id + find_num + refdes` | 组合区分 | find_num/refdes 组合 |
| `child_id_find_num_qty` | `child_id + find_num + quantity` | 数量敏感 | 数量变化视为新增/删除 |
| `line_full` | `child_id + find_num + refdes + effectivity` | 生效区分 | 生效窗口不同视为不同 BOM 行 |

> 注意：`line_full` 会把 find_num/refdes/effectivity 的变化判定为新增/删除，而不是字段级变更。

#### compare_mode（结构对齐策略）

| `compare_mode` | 默认 `line_key` | 属性比较 | 说明 |
|---|---|---|---|
| `only_product` | `child_config` | 无 | 只比较存在性 |
| `summarized` | `child_config` | `quantity`, `uom` | 汇总同一子件数量 |
| `num_qty` | `child_config_find_num_qty` | `quantity`, `uom`, `find_num` | 数量变化视为新增/删除 |
| `by_position` | `child_config_find_num` | `quantity`, `uom`, `find_num` | 按序号对齐 |
| `by_reference` | `child_config_refdes` | `quantity`, `uom`, `refdes` | 按位号对齐 |

### 9.3 BOM 行属性（必须比较）

这些字段主要来自 BOM 关系 Item 的 `properties`（`meta_items.properties`），
若启用替代件/生效性，则需要额外查询关联表。

| 字段 | 含义 | 来源 | 规范化 | 严重度 | 比较规则 |
|---|---|---|---|---|---|
| `quantity` | 用量 | `properties` | `Decimal/float` | `major` | 数值比较（可设置 `1e-6` 容差） |
| `uom` | 单位 | `properties` | `upper().strip()` | `major` | 字符串等值 |
| `find_num` | 序号 | `properties` | `strip()` | `minor` | 字符串等值（保留前导零） |
| `refdes` | 位号 | `properties` | 分隔/去重/排序/大写 | `minor` | 集合等值 |
| `effectivity_from` | 生效起始 | `properties` | ISO→UTC | `major` | 时间等值 |
| `effectivity_to` | 生效结束 | `properties` | ISO→UTC | `major` | 时间等值 |
| `effectivities` | 生效记录 | `meta_effectivities` | list 归一化 | `major` | 需 `include_effectivity=true` |
| `substitutes` | 替代件 | `Part BOM Substitute` | list 归一化 | `minor` | 需 `include_substitutes=true` |
| `extra_properties.*` | 扩展字段 | `properties` | 仅比较白名单字段 | `info` | 深度比较 |

**refdes 规范化建议**：
- 分隔符：`,` `;` `|` 空格 → 统一为逗号
- 去空白、去重复、排序
- 示例：`"R1, R2;R3"` → `["R1","R2","R3"]`

> 规则：`changed[*].severity` 取字段级变更中最高严重度；summary 可统计 `changed_major/minor/info`。

### 9.4 Effectivity（可选增强）

Yuantus 的效期既可能在 `properties` 中，也可能在 `meta_effectivities` 表中。
比较策略：
1. 若提供 `effective_at` 参数：先用效期过滤 BOM，再做 diff。
2. 若不提供：只比较 `effectivity_from/to` 字段是否一致。
3. 若 `include_effectivity=true`：额外比较 `meta_effectivities` 明细列表。

### 9.5 父/子件字段（可选）

默认不比，避免无关字段造成“全量变化”。若业务需要可开启 `include_child_fields=true`：

| 字段 | 来源 | 说明 |
|---|---|---|
| `parent.id` | `meta_items.id` | 父件 ID |
| `parent.config_id` | `meta_items.config_id` | 父件配置 ID |
| `parent.item_number` | `meta_items.properties.item_number` | 父件物料号 |
| `parent.name` | `meta_items.properties.name` | 父件名称 |
| `child.id` | `meta_items.id` | 子件 ID |
| `child.config_id` | `meta_items.config_id` | 子件配置 ID |
| `child.item_number` | `meta_items.properties.item_number` | 子件物料号 |
| `child.name` | `meta_items.properties.name` | 子件名称 |

可选扩展字段（按需启用）：
- `child.state`（生命周期）
- `child.revision`（版本修订）

### 9.6 建议输出结构（供 API 设计）

```json
{
  "summary": {
    "added": 2,
    "removed": 1,
    "changed": 3
  },
  "added": [
    { "parent_id": "...", "child_id": "...", "properties": { ... } }
  ],
  "removed": [
    { "parent_id": "...", "child_id": "...", "properties": { ... } }
  ],
  "changed": [
    {
      "parent_id": "...",
      "child_id": "...",
      "line_key": "...",
      "severity": "major",
      "before": { "quantity": 1, "uom": "EA" },
      "after": { "quantity": 2, "uom": "EA" }
    }
  ]
}
```

> 结论：**BOM Compare 的核心是“稳定身份 + 规范化字段 + 可控的差异噪音”。**

### 9.7 示例输入与输出（含版本维度）

#### 示例 A：按 Item 对比

请求：

```http
GET /api/v1/bom/compare?left_type=item&left_id=<PARENT_A_ID>&right_type=item&right_id=<PARENT_B_ID>&max_levels=10
```

期望返回（示例）：

```json
{
  "summary": { "added": 1, "removed": 0, "changed": 1 },
  "added": [
    {
      "parent_id": "PARENT_B",
      "child_id": "CHILD_X",
      "properties": { "quantity": 2, "uom": "EA" }
    }
  ],
  "removed": [],
  "changed": [
    {
      "parent_id": "PARENT_A",
      "child_id": "CHILD_Y",
      "before": { "quantity": 1, "uom": "EA", "refdes": ["R1"] },
      "after": { "quantity": 2, "uom": "EA", "refdes": ["R1","R2"] }
    }
  ]
}
```

#### 示例 B：按 Version 对比

请求：

```http
GET /api/v1/bom/compare?left_type=version&left_id=<VERSION_1A_ID>&right_type=version&right_id=<VERSION_1B_ID>&max_levels=10
```

期望返回（示例）：

```json
{
  "summary": { "added": 0, "removed": 1, "changed": 2 },
  "added": [],
  "removed": [
    {
      "parent_id": "PARENT_CONFIG",
      "child_id": "CHILD_Z",
      "properties": { "quantity": 1, "uom": "EA" }
    }
  ],
  "changed": [
    {
      "parent_id": "PARENT_CONFIG",
      "child_id": "CHILD_Y",
      "before": { "quantity": 1, "uom": "EA" },
      "after": { "quantity": 2, "uom": "EA" }
    },
    {
      "parent_id": "PARENT_CONFIG",
      "child_id": "CHILD_X",
      "before": { "find_num": "010" },
      "after": { "find_num": "020" }
    }
  ]
}
```

#### 示例 C：错误与边界

1) `left_id` 不存在：

```json
{ "detail": "Item <left_id> not found" }
```

2) 无权限（RBAC）：

```json
{ "detail": "Permission denied" }
```

3) `max_levels=0`：

```json
{
  "summary": { "added": 0, "removed": 0, "changed": 0 },
  "added": [],
  "removed": [],
  "changed": []
}
```

### 9.8 验证脚本草案（verify_bom_compare.sh 模板）

> 说明：这是 **验收脚本模板**，供 Claude 按需替换字段与断言逻辑。

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

echo "==> Seed identity/meta"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
"$CLI" seed-meta >/dev/null

echo "==> Login as admin"
TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"

AUTH=(-H "Authorization: Bearer $TOKEN")
TS="$(date +%s)"

echo "==> Create parent items"
PARENT_A="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-A-$TS\",\"name\":\"Compare A\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
PARENT_B="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-B-$TS\",\"name\":\"Compare B\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"

echo "==> Create children"
CHILD_X="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-X-$TS\",\"name\":\"Child X\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
CHILD_Y="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-Y-$TS\",\"name\":\"Child Y\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"

echo "==> Build BOM A"
$CURL -X POST "$API/bom/$PARENT_A/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_X\",\"quantity\":1,\"uom\":\"EA\"}" >/dev/null
$CURL -X POST "$API/bom/$PARENT_A/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_Y\",\"quantity\":1,\"uom\":\"EA\",\"find_num\":\"010\"}" >/dev/null

echo "==> Build BOM B (changed + added)"
$CURL -X POST "$API/bom/$PARENT_B/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_X\",\"quantity\":2,\"uom\":\"EA\"}" >/dev/null

echo "==> Compare BOM"
RESP="$(
  $CURL "$API/bom/compare?left_type=item&left_id=$PARENT_A&right_type=item&right_id=$PARENT_B&max_levels=10" \
    "${HEADERS[@]}" "${AUTH[@]}"
)"

echo "$RESP" | "$PY" - <<'PY'
import sys, json
d = json.load(sys.stdin)
assert d["summary"]["changed"] >= 1
assert d["summary"]["removed"] >= 1 or d["summary"]["added"] >= 0
print("BOM Compare: OK")
PY

echo "ALL CHECKS PASSED"
```

### 9.9 对比算法草案（实现参考）

1) 获取 BOM 树  
   - `left_type=item` -> `get_bom_structure(item_id, levels=...)`  
   - `left_type=version` -> `get_bom_for_version(version_id, levels=...)`  

2) Flatten 成边集合  
   - 遍历树，得到 `(parent, child, relationship_properties)`  
   - 生成 `edge_key = parent_key + "::" + child_key`  

3) 规范化 BOM 行属性  
   - `quantity`: 数值化 + 容差比较  
   - `uom`: `upper().strip()`  
   - `find_num`: `strip()`  
   - `refdes`: 分隔符统一、去重、排序  
   - `effectivity_from/to`: ISO -> UTC  

4) 计算 diff  
   - `added = right_keys - left_keys`  
   - `removed = left_keys - right_keys`  
   - `changed = intersect(left_keys, right_keys) and props !=`  

5) 输出  
   - summary + added/removed/changed  
   - 建议按 key 排序，保证结果可复现  

### 9.10 参数矩阵（建议）

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `left_type/right_type` | `item|version` | `item` | 比较维度 |
| `left_id/right_id` | `str` | - | 目标 ID |
| `max_levels` | `int` | `10` | 展开深度 |
| `effective_at` | `datetime` | `null` | 可选：按效期过滤后再比较 |
| `include_child_fields` | `bool` | `false` | 是否比较子件字段 |
| `include_substitutes` | `bool` | `false` | 是否比较替代件 |
| `include_effectivity` | `bool` | `false` | 是否比较生效性明细 |
| `include_relationship_props` | `list` | `null` | 只比较白名单 BOM 字段 |

### 9.11 关键测试用例清单

1) **新增**：右侧多一个子件  
2) **删除**：左侧多一个子件  
3) **属性变化**：quantity/uom/find_num/refdes 变化  
4) **深度**：多层 BOM 比较  
5) **max_levels=0**：空 diff  
6) **权限不足**：403  
7) **无效 ID**：404  
8) **跨租户**：数据不串  

### 9.12 版本维度的特殊处理

- `left_type=version` 时优先使用 `version.item_id` 的 BOM  
- 建议使用 `get_bom_for_version()` 来继承效期语义  
- `parent/child` 的 `config_id` 更稳定，避免同一物料不同版本被误判新增/删除  

### 9.13 输出稳定性建议

- 按 `parent_key, child_key` 排序  
- `changed` 中 `before/after` 只保留差异字段（可选优化）  

### 9.14 容错与边界

- 避免循环：flatten 时维护 `visited`  
- 空 BOM：返回空 diff，不报错  
- `max_levels < 0`：可视为无限（或返回 400）  

### 9.15 API 端点草案（建议）

**端点：**

```http
GET /api/v1/bom/compare
```

**查询参数：**

| 参数 | 必填 | 示例 | 说明 |
|---|---|---|---|
| `left_type` | ✅ | `item` | `item` 或 `version` |
| `left_id` | ✅ | `<ITEM_ID>` | 左侧对象 ID |
| `right_type` | ✅ | `item` | `item` 或 `version` |
| `right_id` | ✅ | `<ITEM_ID>` | 右侧对象 ID |
| `max_levels` | ❌ | `10` | 展开深度 |
| `effective_at` | ❌ | `2025-01-01T00:00:00Z` | 效期过滤 |
| `include_child_fields` | ❌ | `false` | 是否比较子件字段 |
| `include_relationship_props` | ❌ | `quantity,uom,find_num,refdes` | 仅比较白名单字段 |

**错误码建议：**

| HTTP | 场景 |
|---|---|
| `400` | 参数非法（type 不支持 / max_levels 负值） |
| `403` | 无权限（ItemType 或 Part BOM 权限不足） |
| `404` | left/right 目标不存在 |
| `422` | 参数类型错误（FastAPI 验证失败） |

**示例请求：**

```bash
curl -s "http://127.0.0.1:7910/api/v1/bom/compare?left_type=item&left_id=<A>&right_type=item&right_id=<B>&max_levels=5&include_relationship_props=quantity,uom,find_num,refdes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: tenant-1" -H "x-org-id: org-1"
```
