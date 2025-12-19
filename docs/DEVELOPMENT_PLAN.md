# YuantusPLM（元图PLM）详细开发计划（Claude 开发 / GPT 验证）

仓库：`yuantus-plm`  
适用：机械行业 PLM（Part/BOM/Version/ECO/Document/CAD Integration）  
目标：先交付“可用、可扩展”的 MVP（模块化单体 + Worker），再按边界拆分专用服务，逐步做到企业级与 SaaS 多租户。

> 说明：本文是“工程开发计划 + 验收/验证计划”。架构设计见 `docs/DEVELOPMENT_DESIGN.md`；可执行验证入口见 `docs/VERIFICATION.md`。

## 当前状态（截至 `2025-12-19`）

已具备“可持续迭代”的交付底座（可私有化部署 + 可验证）：

- ✅ Postgres + Alembic migrations：`yuantus db upgrade`
- ✅ MinIO(S3) upload/download：download 支持 `302 -> presigned URL`
- ✅ Job 并发安全（Postgres `SKIP LOCKED`）
- ✅ docker compose 一键：API + Worker + Postgres + MinIO
- ✅ Run H 全链路脚本：`scripts/verify_run_h.sh`

证据（可复现记录）：

- `docs/VERIFICATION_RESULTS.md`
- `docs/PRIVATE_DELIVERY_REPORT.md`
- `docs/PRIVATE_DELIVERY_ACCEPTANCE.md`

---

## 0) 协作方式（你用 Claude 写代码，我来验证）

### 0.1 交付物约定（每个功能点/PR 的 Definition of Done）

Claude 每次交付至少包含：

- 代码实现（API/Service/Model/Task/Plugin 等）
- **迁移与兼容**：如涉及 DB schema 变更，必须给出迁移方式（短期可 `create_all()`，中期必须 Alembic）
- **验证步骤**：在 `docs/VERIFICATION.md` 增加可复制的命令（curl/CLI/worker）
- **可观测输出**：关键日志字段（tenant/org/job_id/file_id/item_id）
- **失败可解释**：错误码/错误信息可定位（尤其 CAD/外部服务任务）

我（GPT）负责：

- 按 `docs/VERIFICATION.md` 在本机复现与验证（API + worker + 关键流程）
- 把“实际执行记录”写入 `docs/VERIFICATION_RESULTS.md`（带时间、端口、关键 ID、HTTP code）
- 对不符合 DoD 的交付给出“阻塞项清单 + 最小修复建议”

### 0.2 交付节奏建议

- 每次交付控制在 **1～3 个功能点**，避免“一次性大改”难以验证与回滚。
- 每个功能点必须是“可验证闭环”：**写入数据 → 查询/回读 → 权限校验 → 异步任务（如有）完成 → 结果可读**。

### 0.3 验证产物格式（强约束，方便回归）

Claude 每个 Sprint 结束时，请至少提供：

- ✅ 一个可执行脚本：`scripts/verify_<sprint_or_feature>.sh`
- ✅ 一段可复制命令块：追加到 `docs/VERIFICATION.md`
- ✅ 我执行后的真实结果：我会写入 `docs/VERIFICATION_RESULTS.md`（包含摘要表）

---

## 1) 版本里程碑（建议按 2 周一个 Sprint）

下面计划以 “S0～S7（共 8 个 Sprint，约 16 周）” 为主线；你也可以把多个 sprint 合并/拆分。

### S0（第 0～2 周）：工程底座与交付形态（必须先稳住）

**目标**：从 dev demo 过渡到“可持续开发”的工程体系。

交付清单：

- 配置体系固化：`YUANTUS_*` 环境变量清单（新增/弃用要记录）
- 依赖与运行矩阵：Python 版本、OS（mac/linux）、是否需要 FreeCAD
- Docker 形态明确：
  - `docker-compose.yml`：本地依赖（Postgres/MinIO/Redis）
  - API/Worker 是否需要容器化（建议至少提供示例 Dockerfile）
- 日志标准：request_id、tenant_id、org_id、user_id、job_id、trace
- 文档：新增 `docs/RUNBOOK_DEV.md`（可选）

验收/验证（我执行）：

- `GET /api/v1/health` 在 `7910` 可用
- `YUANTUS_AUTH_MODE=required` 下登录与受保护接口可用
- `yuantus worker --once` 可正常处理一个 demo job

> 注：S0/S2 的“私有化交付底座”（Postgres+MinIO+Alembic+compose）已完成并通过复核，详见 `docs/PRIVATE_DELIVERY_REPORT.md`。

### S1（第 3～4 周）：元模型（Meta）与权限（RBAC）强化

**目标**：形成“Aras 风格的元数据驱动 + 可配置权限”最小闭环。

交付清单：

- Meta Schema 管理能力（ItemType/Property/Relationship）补齐缺口
- PermissionSet/ACE 的可视化/可操作 API（最少：创建、配置、绑定 ItemType）
- 元模型变更的审计（最少：created_at/updated_at/created_by）

验收/验证：

- `seed-meta` 后能创建新 ItemType，并用 AML/RPC 创建/查询实例
- RBAC 生效：不同角色对同一 ItemType 的 create/update 被允许/拒绝

### S2（第 5～6 周）：文件与文档（Document）产品化

**目标**：让文件/图纸/模型成为可追溯资产，支撑 CAD 与变更。

交付清单：

- FileContainer 强化：角色（主模型/图纸/附件/打印件）、元数据（作者、版本、来源系统）
- S3/MinIO 模式可跑通（presigned url/下载/预览路径）
- 防护能力（至少其一）：
  - 上传大小限制/类型白名单
  - checksum 去重策略与引用计数（可后置）

验收/验证：

- local + s3 两种存储模式各跑通一次 upload/download
- Item 挂载文件列表可回读

> 注：S2 的 MinIO(S3) upload/download 已跑通，并已纳入 `scripts/verify_run_h.sh` 覆盖（S3 模式 download 为 `302->200`）。

### S3（第 7～8 周）：BOM（多级）+ 版本（Revision）强化

**目标**：机械行业主干：EBOM 多级、版本树、有效性。

建议把 S3 拆成 3 个可独立验收的小目标（Claude 每次交付 1 个，避免一次性大改难以回归）：

**S3.1 多级 BOM API + 循环检测**

- 数据模型（最小字段集）：BOM 行支持 `qty/uom/find_num/refdes`
- API（命名可调整，但需稳定契约）：
  - `POST /api/v1/bom/{parent_id}/children`（add child）
  - `DELETE /api/v1/bom/{parent_id}/children/{child_id}`
  - `GET /api/v1/bom/{parent_id}/tree?depth=...`
- 规则：
  - 循环检测：A→B→C→A 必须被拒绝（HTTP 409 + 返回循环路径）
- 验证脚本：
  - `scripts/verify_bom_tree.sh`：创建 3 层 BOM + 循环用例

**S3.2 Effectivity（效期/生效性）最小可用**

- 数据模型：BOM 行支持 `effectivity_from/effectivity_to`
- API：`GET /api/v1/bom/{parent_id}/effective?at=...`（默认 now）
- 验证脚本：
  - `scripts/verify_bom_effectivity.sh`：未来生效/失效用例

**S3.3 版本语义与规则固化**

- 版本规则（先固化 1 套，后续可配置）：
  - `rev`（A/B/C）+ `iteration`（.1/.2），或沿用现有 label 规则，但需文档化
  - 新版本与文件/图纸绑定的最小规则：主模型/图纸随版本冻结
- API：
  - `GET /api/v1/versions/items/{item_id}/history|tree`（已存在则补强断言）
  - 如需独立 API：`POST /api/v1/versions/items/{item_id}/new-revision`（或复用 ECO）
- 验证脚本：
  - `scripts/verify_versions.sh`

交付清单：

- 多级 BOM：增删改查、展开（递归）、循环检测
- Effectivity（已有效/未来生效/失效）在 BOM 查询中体现（至少接口与模型就位）
- 版本语义明确：
  - Item 的 `rev`/`generation` 规则
  - 新版本与文件/图纸绑定规则

验收/验证：

- 创建 A→B→C 三层 BOM，查询 effective BOM 返回正确树
- 创建新版本后，历史/树接口能展示（且权限不穿透）

### S4（第 9～10 周）：ECO/Workflow（工程变更）闭环强化

**目标**：把“版本 + BOM + 文档 + 权限”串成工程变更闭环。

交付清单：

- ECO 影响分析（最少：涉及 Item、涉及 BOM、涉及文件）
- ECO 状态机/审批流（最少：draft → review → approved → applied）
- Apply 规则：
  - 生成新版本
  - 更新 BOM/附件绑定
  - 写入审计记录

验收/验证：

- ECO 创建 → 新版本 → 审批 → Apply 后数据一致可追溯
- 被拒绝/冲突场景返回可解释错误

### S5（第 11～12 周）：CAD 集成 MVP（真实业务可用）

**目标**：把“CAD 文件进入 PLM → 预览/几何 → 属性抽取 → 绑定版本”跑通。

强烈建议把 S5 分成 “平台能力” 与 “连接器能力” 两条线并行推进：

#### S5-A（平台）：CAD Pipeline 与存储无关（Local/S3 都可跑）

这是 **必须优先** 的能力：否则私有化 S3 环境下 CAD 任务（preview/geometry/dedup/ml）不可用。

- 输入文件获取：
  - Local：直接读 `LOCAL_STORAGE_PATH`
  - S3：Worker 能把 `system_path` 下载到临时目录（scratch），执行转换后清理
- 输出文件回写：
  - preview/geometry 生成后：
    - Local：写入 vault
    - S3：upload 回 S3，并把 `preview_path/geometry_path` 记录为 object key
- 下载/预览端点补齐（S3）：
  - `GET /api/v1/file/{id}/preview`：S3 模式支持 `302` 或 stream
  - `GET /api/v1/file/{id}/geometry`：S3 模式支持 `302` 或 stream
- 验证脚本（必须新增）：
  - `scripts/verify_cad_pipeline_s3.sh`：上传文件 → 创建 preview job → worker 执行 → preview 可回读（200 或 302->200）

#### S5-B（连接器）：主流 CAD 对接策略（先 1 个 CAD 打样）

推荐策略：**CAD 插件只负责 UI/采集，本机 Agent/CLI 负责网络与协议**（便于统一认证、缓存、重试与离线队列）。

- 组件：
  - CAD 插件（SolidWorks/AutoCAD/...）：获取当前模型路径/元数据 → 调用本机 Agent
  - 本机 Agent（建议先复用 `yuantus` CLI 增子命令，后续可独立 `yuantus-agent`）：
    - 登录/缓存 token
    - 文件上传（预留断点续传）
    - 调用 `cad/import` 并轮询任务/结果
    - 出错提示与重试
- 第一阶段（打样 CAD 选择）：
  - 3D：SolidWorks 或 Inventor（机械行业高频）
  - 2D：AutoCAD/ZWCAD（图纸高频）
- 验证（最少）：
  - 无 CAD 环境也可跑：上传一个文件 + 模拟 metadata（作为 CI/回归）
  - 有 CAD 环境再补充真实插件验证步骤（放 `docs/VERIFICATION.md` 的附录）

交付清单（按优先级）：

1) **导入编排**（已具备雏形）：
   - `POST /api/v1/cad/import` 支持 item_id 挂载
   - 任务选择（preview/geometry/dedup/ml）参数固化与校验
2) **转换能力产品化**：
   - geometry：`step/stp/iges/igs` → `gltf`（优先）
   - preview：优先真实预览（FreeCAD/Pillow/trimesh），无依赖时占位图
3) **CAD 元数据抽取接口（先占位）**：
   - 从文件名/自定义映射提取基础属性（item_number、name、material…）
   - 预留从外部解析服务抽取属性的接口（后续替换）
4) **2D 图纸去重**（对接 `dedupcad-vision`）：
   - 结果写入 job.result，并可选写入“相似图纸关系”

验收/验证（我执行）：

- `cad/import` → `cad_preview` → `GET /file/{id}/preview` 返回 `200`
- 具备 FreeCAD 环境时（或在转换容器中）：`cad_geometry` 产出 `gltf/glb`
- `cad_dedup_vision` 返回 top-k 相似结果，且不会触发重试风暴

### S6（第 13～14 周）：搜索/索引与报表能力

**目标**：工程数据可检索、可统计，支撑大规模使用。

交付清单：

- SearchEngine 接口稳定（DB fallback → OpenSearch/ES 可插拔）
- Index 任务：Item/Doc/File/BOM 变更后增量索引（建议 outbox 或 job）
- 报表/RPC：按 ItemType/状态/ECO 阶段聚合统计

验收/验证：

- 关键对象创建后可按关键词搜索（item_number/name/图号）
- BOM 与 ECO 能被检索到（至少 id/标题/状态）

### S7（第 15～16 周）：私有化交付 + SaaS 多租户运营能力（基础版）

**目标**：可部署、可升级、可观察、可隔离。

交付清单：

- 私有化：
  - docker-compose 一键启动（API + Worker + Postgres + MinIO）
  - 备份/恢复手册（DB + 对象存储）
- 多租户：
  - tenant/org provisioning API（创建/禁用）
  - 基础配额模型（用户数、存储、任务并发）与拒绝策略（先软限制）
- 可观测：
  - job 指标（成功/失败/耗时）
  - 外部服务调用指标（可选熔断）

验收/验证：

- compose 启动后一条龙验证（health/login/seed-meta/cad/import/worker）
- db-per-tenant（或 db-per-tenant-org）下同一接口在不同租户数据不串

---

## 2) 增补：面向机械行业的“必须功能清单”（建议作为长期 Backlog）

> 这些不一定全部进 S0～S7，但建议作为需求池，用来评估“超越 Aras”的路线图与优先级。

- 配置管理：选配/变型（Variant/Options）、替代件（Substitute）、等效件（Equivalent）
- 版本控制：BOM 差异对比（Diff）、基线（Baseline）、回滚与追溯
- 工艺与制造：MBOM、工艺路线（Routing）、工序文件、工装夹具、工艺更改（ECN）
- 质量与合规：偏差/不合格（NCR）、CAPA、签署与电子签名（eSign）
- 集成：ERP（SAP/用友/金蝶）、MES、PDM 迁移工具（Aras/Teamcenter/Windchill）

---

## 3) 模块拆分建议（什么时候拆微服务）

当前优先“模块化单体 + worker”。当出现以下信号时拆服务：

- CAD 转换需要大量 CPU/GPU/依赖（FreeCAD、商业 SDK）→ 拆 `cad-convert-service`
- 去重/ML 属于独立迭代路线 → 拆 `cad-vision-service`（或直接依赖现有外部服务）
- 搜索需要独立扩缩容 → 拆 `search-service`（或独立 ES）

拆分原则：

- 核心真相源（Item/BOM/Version/ECO/File 关系）不拆出 core
- 外围服务只产出“派生数据”（preview/geometry/embedding/ocr），通过 job.result 回写

---

## 4) 验证策略（我如何验证每个 Sprint）

### 4.1 验证分层

- **API 合同验证**：OpenAPI 路由存在、HTTP code 正确、错误信息可解释
- **数据一致性验证**：创建→查询→权限→变更后回读一致
- **异步任务验证**：创建 job → worker 执行 → job 状态完成且 result 可用
- **隔离验证**：tenant/org 维度不串库/不串数据

### 4.2 文档化要求

- `docs/VERIFICATION.md`：新增每个功能点的可复制命令
- `docs/VERIFICATION_RESULTS.md`：我会追加“实际运行记录”（时间、端口、关键 ID、HTTP code）

---

## 5) 风险清单与缓解

- CAD 转换依赖复杂（FreeCAD/cadquery/商业 SDK）：
  - 缓解：先把转换放到独立镜像/节点；core 只编排任务与追溯
- 多租户数据隔离策略演进（sqlite → Postgres）：
  - 缓解：保持 tenant/org 上下文与 `resolve_database_url()` 契约不变，切换只影响 infra
- 需求膨胀（“超越 Aras”）：
  - 缓解：严格以“机械行业主干闭环”（Part/BOM/Rev/ECO/Doc/CAD）作为里程碑验收

---

## 附录 A：建议新增的验证脚本清单（Claude 实现 / GPT 执行）

| 脚本 | 覆盖能力 | 关键断言 |
|---|---|---|
| `scripts/verify_run_h.sh` | 核心全链路 | `ALL CHECKS PASSED` |
| `scripts/verify_bom_tree.sh` | 多级 BOM | depth/tree/循环检测 |
| `scripts/verify_bom_effectivity.sh` | BOM 效期 | `at=...` 返回正确 children |
| `scripts/verify_versions.sh` | 版本 | history/tree 正确 |
| `scripts/verify_permissions.sh` | RBAC/ACE | 角色差异 `200` vs `403` |
| `scripts/verify_cad_pipeline_s3.sh` | CAD pipeline + S3 | preview/geometry 可回读（`200` 或 `302->200`） |
| `scripts/verify_multitenancy.sh` | tenant/org 隔离 | tenantA 与 tenantB 数据不串 |
