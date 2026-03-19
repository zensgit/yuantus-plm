# Yuantus Odoo18 PLM Parallel Execution Design

## Architecture Baseline
- `src/yuantus/api/app.py`: top-level router registration
- `src/yuantus/meta_engine/web/locale_router.py`: locale/report locale CRUD endpoints
- `src/yuantus/meta_engine/locale/service.py`: translation storage
- `src/yuantus/meta_engine/report_locale/service.py`: report locale profile resolution
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`: workorder export implementation
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`: workorder export API

## Increment 2026-03-18 C6-Integration-And-P2A-Workorder-Locale

### Why
- Claude 已完成 `C6`，但当前主线基线里没有 locale/report 能力。
- 当前真实代码里最适合接 locale 的现有出口是 `workorder-docs/export`。
- 这条链路已存在 `json/pdf/zip` 三种导出形态，适合把 report locale 先产品化。

### Delivered Scope
- `locale_router` 接入主应用
- locale/report locale 模型、服务、router tests 可运行
- `workorder-docs/export` 支持显式 locale 解析
- zip 导出新增 `locale.json`
- json manifest 新增 `locale`
- pdf 导出正文新增 locale section

### Interface Contract
- `GET /api/v1/locale/translations`
- `POST /api/v1/locale/translations`
- `POST /api/v1/locale/translations/bulk`
- `GET /api/v1/locale/report-profiles`
- `POST /api/v1/locale/report-profiles`
- `GET /api/v1/locale/report-profiles/resolve`
- `GET /api/v1/workorder-docs/export`

### Workorder Export Locale Rules
- 默认 contract 不变
- 仅当传入以下任一参数时才启用 locale 解析：
  - `report_lang`
  - `report_type`
  - `locale_profile_id`
- 解析优先级：
  1. `locale_profile_id` -> `get_profile`
  2. `report_lang + report_type` -> `resolve_profile`
- 若未找到 profile：
  - 不报错
  - 导出继续
  - `manifest.locale` 不生成

### Failure Modes
- router 未注册：`test_locale_router.py` 会直接失败
- locale profile 缺失：manifest 不带 locale，但导出成功
- query 参数未传：保持原有 workorder export contract

### Non-Goals
- 本轮不做 item description translation 落库消费
- 本轮不做 BOM/export locale 全域接入
- 本轮不动 Claude 正在进行的 `C7`

## Increment 2026-03-18 P2A-Parallel-Ops-Locale

### Why
- `parallel-ops/summary` 与 `parallel-ops/trends` 是当前真实代码里第二条稳定导出链。
- `P2-A` 如果只停在 `workorder-docs/export`，locale 仍然只是单点能力，不足以支撑跨导出管线复用。
- 这条链完全位于 `parallel_tasks` 写域，适合在不干扰 Claude 的前提下继续推进。

### Delivered Scope
- `ParallelOpsOverviewService.export_summary(...)` 支持 locale 解析
- `ParallelOpsOverviewService.export_trends(...)` 支持 locale 解析
- `parallel-ops` 两个导出路由支持：
  - `report_lang`
  - `report_type`
  - `locale_profile_id`
- JSON / Markdown 增加 locale 输出
- CSV contract 保持不变

### Locale Export Rules
- 显式传 locale 参数时才尝试解析 profile
- 解析优先级保持与 `workorder-docs/export` 一致：
  1. `locale_profile_id`
  2. `report_lang + report_type`
- 若 profile 不存在：
  - 导出继续
  - 不抛 4xx
  - JSON / Markdown 都不生成 locale block

### Failure Modes
- router 未透传 locale 参数：router contract tests 会失败
- service 未附带 locale：JSON / Markdown locale assertions 会失败
- CSV 被意外修改：既有 CSV 断言会失败

### Non-Goals
- 本轮不把 locale 接入 breakage export / maintenance export
- 本轮不做 locale-aware 数字格式化或日期格式化渲染

## Increment 2026-03-18 P2A-Breakage-Metrics-Locale

### Why
- `breakage metrics` 是当前真实代码里另一条稳定的运维/分析导出链。
- 如果 locale 只覆盖 `workorder` 和 `parallel-ops`，就还没有证明 locale helper 可以跨故障分析导出复用。
- 这条链仍在 `parallel_tasks` 写域，不和 Claude 正在进行的 `C9` 冲突。

### Delivered Scope
- `BreakageIncidentService.export_metrics(...)` 支持 locale 解析
- `BreakageIncidentService.export_metrics_groups(...)` 支持 locale 解析
- `breakage` 两个导出路由支持：
  - `report_lang`
  - `report_type`
  - `locale_profile_id`
- JSON / Markdown 增加 locale 输出
- CSV contract 保持不变

### Locale Export Rules
- 显式传 locale 参数时才尝试解析 profile
- 解析优先级与已有导出链保持一致：
  1. `locale_profile_id`
  2. `report_lang + report_type`
- 若 profile 不存在：
  - 导出继续
  - JSON / Markdown 不生成 locale block
  - 不改变 CSV

### Failure Modes
- router 未透传 locale 参数：router contract tests 会失败
- service 未附带 locale：JSON / Markdown locale assertions 会失败
- CSV contract 被意外修改：既有 CSV 断言会失败

### Non-Goals
- 本轮不接入 breakage incidents export
- 本轮不做 locale-aware 数值/日期格式渲染
- 本轮不触碰 Claude 的 `C9` / `C10` 分支

## Increment 2026-03-18 P2A-Breakage-Incidents-Locale

### Why
- `breakage incidents export` 是 breakage 域最直接的明细导出链。
- 在 `breakage metrics/groups` 已接 locale 之后，再补 incidents，能让 breakage 域形成完整的 locale 导出闭环。
- 这条链仍位于 `parallel_tasks` 写域，继续避开 Claude 的 `C9` / `C10`。

### Delivered Scope
- `BreakageIncidentService.export_incidents(...)` 支持 locale 解析
- `GET /api/v1/breakages/export` 支持：
  - `report_lang`
  - `report_type`
  - `locale_profile_id`
- JSON / Markdown 增加 locale 输出
- CSV contract 保持不变

### Locale Export Rules
- 显式传 locale 参数时才尝试解析 profile
- 解析优先级与前几条导出链一致：
  1. `locale_profile_id`
  2. `report_lang + report_type`
- 若 profile 不存在：
  - 导出继续
  - JSON / Markdown 不生成 locale block
  - CSV 不变

### Failure Modes
- router 未透传 locale 参数：router contract tests 会失败
- service 未附带 locale：JSON / Markdown locale assertions 会失败
- CSV contract 被意外修改：既有 CSV 断言会失败

### Non-Goals
- 本轮不把 locale 接到 breakage export jobs pipeline
- 本轮不做 locale-aware 数字/日期格式渲染

## Increment 2026-03-18 C10-Locale-Resolver

### Why
- 现有 `C6 + P2-A` 已经把 locale profile 接到多个导出链，但 locale 域自身还缺少统一的 resolve/fallback/export-context 工具面。
- `C10` 正好补的是 locale 读侧能力，不会和当前 `parallel_tasks` 写域冲突。
- 当前分支已经是 locale 主分支，适合优先做 Codex 侧集成验证。

### Delivered Scope
- `LocaleService` 新增：
  - `resolve_translation(...)`
  - `resolve_translations_batch(...)`
  - `fallback_preview(...)`
- `ReportLocaleService` 新增：
  - `get_export_context(...)`
- `locale_router` 新增：
  - `POST /locale/translations/resolve`
  - `GET /locale/translations/fallback-preview`
  - `GET /locale/export-context`

### Resolve Rules
- fallback chain 由调用方显式传入
- primary lang 优先，随后按 `fallback_langs` 顺序尝试
- 若无匹配：
  - resolve 返回 `resolved=false`
  - export context 返回 `resolved=false` + 安全默认值

### Failure Modes
- router 未透传 fallback chain：router tests 会失败
- locale service 未保留 resolution chain：fallback preview tests 会失败
- export context 默认值漂移：report locale service tests 会失败

### Non-Goals
- 本轮不做自动翻译
- 本轮不做 description write-back
- 本轮不做跨域消费端接线，先只提供稳定 locale contract

## Increment 2026-03-19 C7-C8-C9-Cross-Regression

### Why
- `C7/C8/C9` 已经分别进入独立 Codex 集成 worktree，但还需要一轮统一口径的回归确认。
- 这轮目标不是增加功能，而是确认三个集成分支都达到了“可合并”状态。

### Delivered Scope
- `C7`：
  - summarized snapshot regression pack promoted to tracked tests
  - regression expanded to include existing BOM delta tests
- `C8`：
  - `quality_router` registered in `create_app()`
  - Pydantic v2 `dict()` deprecation removed
- `C9`：
  - imported missing `maintenance` model package from `C5`
  - `maintenance_router` registered in `create_app()`

### Non-Goals
- 本轮不合并这些分支回 `main`
- 本轮不修改 Claude 的原 feature branches

## Increment 2026-03-19 C7-C8-C9-Stack Integration

### Why
- 分支级回归已经分别通过，但这还不等于单一工作树可合并。
- 需要一条统一集成栈验证真实 cherry-pick 顺序、共享 router 注册点和 path-guard contract。

### Delivered Scope
- 从 `feature/codex-p2a-locale-export` 新开 `feature/codex-stack-c7c8c9`
- 按顺序叠加：
  - `C9` maintenance integration
  - `C8` quality integration
  - `C7` BOM summarized snapshot integration
- 把 stack 上的真实冲突固定到两个文件：
  - `contracts/claude_allowed_paths.json`
  - `src/yuantus/api/app.py`

### Conflict Resolution
- `contracts/claude_allowed_paths.json`
  - 保留 locale 基线里的 `C1-C13` 全量 profile
  - 不回退到 `C8/C9` 分支里的较早 profile 子集
- `src/yuantus/api/app.py`
  - 同时保留 `locale_router`
  - 同时注册 `maintenance_router`
  - 同时注册 `quality_router`

### Chosen Defaults
- 统一集成栈继续以 locale/export 分支为基线
- `C7/C8/C9` 不再视为“仅在独立集成分支完成”，而是视为“已在 stack 分支合并验证”
- Claude 下一批任务优先级固定为：
  - `C11`
  - `C12`
  - `C13`

### Non-Goals
- 本轮不把 stack 直接回合并到主仓脏工作树
- 本轮不扩展 `C11/C12/C13` 的实现

## Claude Task Draft C11

### Why
- 当前已有 `viewer_readiness`、`geometry/assets`、`cad_manifest_url`、`cad_viewer_url`。
- 但缺少面向消费端的导出/summary/readiness 聚合工件。

### Write Scope
- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`

### Target Deliverables
- `viewer_readiness` export payload
- `geometry/assets` pack summary
- consumer-ready aggregate field in file metadata/read model

### Non-Goals
- 不碰 `parallel_tasks`
- 不碰 `quality` / `maintenance` / `locale`

## Claude Task Draft C12

## Increment 2026-03-19 C11-C12 Integration Stack

### Why
- `C11` 和 `C12` 都已经在 Claude 分支完成，但还没有在统一集成栈上验证。
- `C11` 不是纯 router 增量，它依赖 `CADConverterService.assess_viewer_readiness(...)`。
- `C12` 是独立绿地模块，但如果不注册到 `create_app()`，它就只是分支级可用，不是主应用可用。

### Delivered Scope
- `C11`
  - `FileMetadata` 增加 `viewer_readiness`
  - 新增消费端读侧：
    - `GET /file/{file_id}/consumer-summary`
    - `POST /file/viewer-readiness/export`
    - `POST /file/geometry-pack-summary`
  - 在当前集成栈补回 `CADConverterService.assess_viewer_readiness(...)`
- `C12`
  - 新增 `approvals` 绿地模块：
    - category
    - request
    - transition
    - summary
  - `approvals_router` 注册进 `create_app()`
  - app-level router smoke test 覆盖注册结果

### Conflict Resolution
- `contracts/claude_allowed_paths.json`
  - 保留 stack 分支已有的完整 `C1-C13` profile
  - 不接受 `C11/C12` 分支里的收窄版本
- `src/yuantus/meta_engine/web/file_router.py`
  - 保留 stack 分支已有 file router 主体
  - 只并入 `viewer_readiness` field 和 C11 端点块

### Chosen Defaults
- `C11` 的服务契约只补 `assess_viewer_readiness(...)`
- 不把 Claude 分支里的其他 CAD conversion rule 扩展一并混入当前栈
- `C12` 维持 entity-agnostic approval bootstrap，不直接耦合 ECO 热文件

### Non-Goals
- 本轮不把 approvals 接到 ECO / quality / purchase 写侧
- 本轮不扩展 C11 到新的 3D 编辑能力

## Increment 2026-03-19 Unified Stack C7-C13

### Why
- `C7-C13` 已分别在多个 Codex 分支完成集成验证，但还需要确认单一 stack 分支上的真实可组合性。
- 这轮目标是把 `BOM + quality + maintenance + locale + subcontracting + file viewer + approvals` 放到同一分支上，用统一回归来证明边界没有互相踩坏。

### Delivered Scope
- 以 `feature/codex-stack-c11c12` 作为当前统一集成栈
- 确认 ancestry 关系：
  - locale/export 基线
  - `C7-C9` stack
  - `C13`
  - `C11/C12`
- 在统一栈上完成跨域回归，而不再只看单任务包定向测试

### Chosen Defaults
- 继续以 stack 分支作为后续合并准备基线
- 暂停给 Claude 分配新任务，直到当前 stack 进入合并窗口

### Non-Goals
- 本轮不再引入新功能
- 本轮不新开 `C14+` 任务

## Increment 2026-03-19 Unified Stack Regression Automation

### Why
- `C7-C13` 已进入统一 stack 集成态，继续依赖人工拼接长命令做验证，效率低且容易漏包。
- `C14-C16` 回来后仍会复用同一条统一栈，需要一个稳定、可复用、可放进 CI 的入口。

### Delivered Scope
- 新增本地脚本：
  - `scripts/verify_odoo18_plm_stack.sh`
- 新增手动 workflow：
  - `.github/workflows/odoo18-plm-stack-regression.yml`

### Chosen Defaults
- 脚本默认模式是 `full`
- `full` 复用当前已验证通过的统一栈测试包
- `smoke` 只保留 app/router 级快速健康检查
- workflow 暂时只开放 `workflow_dispatch`

### Non-Goals
- 本轮不改现有 `regression.yml`
- 本轮不把统一栈专用回归强行并入全仓 CI 默认路径

## Next Claude Batch C14-C16

### Why
- `C7-C13` 已经进入统一 stack 验证态，继续让 Claude 回写这些域只会增加冲突。
- 现在更适合把 Claude 转到新一批低耦合增量：
  - approvals export
  - subcontracting analytics
  - quality SPC analytics

### Task Boundaries
- `C14`
  - 只允许扩展 `approvals` 域内部读侧、导出和 ops-report
- `C15`
  - 只允许扩展 `subcontracting` 域内部统计、导出和队列概览
- `C16`
  - 只允许扩展 `quality` 域内部 SPC / analytics

### Chosen Defaults
- 不给 Claude 分配新的跨域 orchestration 任务
- 不让 Claude 修改 `parallel_tasks`、`version`、`benchmark_branches`
- 继续用 path guard profile 强约束新任务边界

## Increment 2026-03-19 C14-C15 Unified Stack Integration

### Why
- `C14/C15` worker 都已返回明确契约，但分支 ref 没有同步到主仓 refs。
- 为避免集成窗口被 branch 同步问题卡住，直接按 worker 交付契约在统一栈复刻并验证。

### Delivered Scope
- `approvals` 新增导出和 ops-report：
  - requests export
  - summary export
  - ops-report
  - ops-report export
- `subcontracting` 新增 analytics/export：
  - overview
  - vendor analytics
  - receipt analytics
  - overview/vendors/receipts export

### Chosen Defaults
- `C14` 导出支持：
  - `json`
  - `csv`
  - `markdown`
- `C15` 导出支持：
  - `json`
  - `csv`
- `C15` 继续复用已存在的 `subcontracting_router` 主应用注册，不回退到局部 `FastAPI.include_router(...)` 证明路径

### Non-Goals
- 本轮不引入 `approvals` 到 ECO 热路径
- 本轮不改制造核心服务
- 本轮不做 `subcontracting` 持久化账本增强

## Increment 2026-03-19 C16 Unified Stack Integration

### Why
- `C16` 是 `quality` 域里的纯增量读侧，天然适合直接并入统一栈。
- 统一栈脚本如果不把 `quality analytics / SPC` 纳进去，后续回归基线就不完整。

### Delivered Scope
- cherry-pick `72d4134`
- 新增：
  - `src/yuantus/meta_engine/quality/analytics_service.py`
  - `src/yuantus/meta_engine/quality/spc_service.py`
  - `src/yuantus/meta_engine/web/quality_analytics_router.py`
  - `src/yuantus/meta_engine/tests/test_quality_analytics_service.py`
  - `src/yuantus/meta_engine/tests/test_quality_analytics_router.py`
  - `src/yuantus/meta_engine/tests/test_quality_spc_service.py`
- 主应用注册：
  - `src/yuantus/api/app.py`
- 统一栈脚本扩容：
  - `scripts/verify_odoo18_plm_stack.sh`

### Chosen Defaults
- analytics router 与现有 `quality_router` 并行存在，不回写原有 CRUD 契约
- path guard 冲突按统一栈更宽边界收口：
  - 保留 `quality_router`
  - 追加 `quality_analytics_router`
- 统一栈脚本继续默认跑 `full`

### Non-Goals
- 本轮不把质量统计联到 `parallel_tasks`
- 本轮不把质量统计回写制造热路径

## Increment 2026-03-19 Merge Prep Broader Regression

### Why
- `C14/C15/C16` 已进入统一栈，当前最重要的不是继续开新支线，而是证明这条栈足够稳定，可以进入 merge-prep。
- 统一栈脚本主要覆盖 stack 内模块，还需要额外把 `parallel_tasks` locale/export 这类跨域包一起拉进来。

### Delivered Scope
- 增加一轮 merge-prep broader regression：
  - stack 脚本覆盖域
  - `parallel_tasks` locale/export pack
- 形成独立 merge-prep 工件：
  - `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`

### Chosen Defaults
- merge-prep 热点优先按“最容易冲突且最常变”的文件收敛：
  - `src/yuantus/api/app.py`
  - `contracts/claude_allowed_paths.json`
  - 共享 `PLAN/DESIGN/VERIFICATION`
  - `docs/DELIVERY_DOC_INDEX.md`
- 现阶段不再开新 Claude 任务，先把统一栈送进最终回归与合并窗口

### Non-Goals
- 本轮不做最终主仓合并
- 本轮不追加新的功能面

## Next Claude Batch C17-C19

### Why
- `feature/codex-merge-rehearsal-stack` 已完成无冲突合并演练。
- 当前主栈可以冻结进入 merge-prep，因此允许 Claude 重新开新任务，但只能开全新绿地子域。

### Task Boundaries
- `C17`
  - 只允许扩展 `box` 子域
- `C18`
  - 只允许扩展 `document_sync` 子域
- `C19`
  - 只允许扩展 `cutted_parts` 子域

### Chosen Defaults
- `C17-C19` 一律不允许编辑：
  - `src/yuantus/api/app.py`
  - `parallel_tasks`
  - `version`
  - `benchmark_branches`
  - 当前已集成 router 热文件
- Claude should branch greenfield work from the frozen base:
  - `feature/claude-greenfield-base`
  - freeze commit `9b312e3`
- Do not branch `C17-C19` from `main`, because `main` lacks the prepared guard/docs context

### Non-Goals
- 本轮不把 `C17-C19` 直接叠到统一栈
- 本轮不定义新的跨域 orchestration

## Merge-Prep Freeze Policy

### Why
- `feature/codex-merge-rehearsal-stack` 已证明统一栈可无冲突合入 `main`。
- 当前阶段的主要风险已从功能实现转为：
  - merge hotspot review
  - regression drift
  - branch discipline

### Chosen Defaults
- `feature/codex-stack-c11c12` 只接受：
  - merge-prep 文档更新
  - regression refresh
  - 必要的 integration bugfix
- 新功能一律转移到新的绿地 Claude 分支或后续独立 Codex 集成分支

### Non-Goals
- 本轮不继续在统一栈上叠 `C17-C19` 实现
- 本轮不把统一栈重新当成主功能开发分支

### Why
- 现有仓库只有 ECO approvals，不存在独立的 generic approvals 模块。
- 这条线适合用全新模块落地，避免挤占现有热文件。

### Write Scope
- new `src/yuantus/meta_engine/approvals/`
- new `src/yuantus/meta_engine/web/approvals_router.py`
- new approval tests

### Target Deliverables
- approval category
- approval request
- request state machine
- pending/list/detail endpoints

### Non-Goals
- 不修改 `eco_router.py`
- 不修改 `eco_service.py`

## Claude Task Draft C13

### Why
- 当前制造模型已有 `is_subcontracted` / `subcontractor_id` 痕迹，但没有独立 subcontracting 模块。
- 用 bootstrap 方式先做独立读模型和最小路由，冲突最低。

### Write Scope
- new `src/yuantus/meta_engine/subcontracting/`
- new `src/yuantus/meta_engine/web/subcontracting_router.py`
- new subcontracting tests

### Target Deliverables
- subcontract order read model
- vendor assignment
- material issue/receipt skeleton
- list/detail endpoints

### Non-Goals
- 第一轮不改 `manufacturing/routing_service.py`
- 第一轮不做复杂 MRP orchestration

## Increment 2026-03-19 C13-Subcontracting Bootstrap

### Why
- 现有制造模型已经有 `is_subcontracted` / `subcontractor_id` 痕迹，但没有独立 subcontracting 域。
- 这条线适合用 net-new 模块落地，避免和 Claude 正在进行的 `C11/C12` 写域冲突。

### Delivered Scope
- new `src/yuantus/meta_engine/subcontracting/models.py`
- new `src/yuantus/meta_engine/subcontracting/service.py`
- new `src/yuantus/meta_engine/web/subcontracting_router.py`
- app registration in `src/yuantus/api/app.py`
- service/router/app smoke tests

### Chosen Defaults
- 只复用 `Operation.routing_id`、`Operation.is_subcontracted`、`Operation.subcontractor_id`
- 不改 `manufacturing/routing_service.py`
- 订单状态只覆盖 bootstrap 必需闭环：
  - `draft`
  - `issued`
  - `partially_received`
  - `completed`

### Delivered Contract
- `POST /api/v1/subcontracting/orders`
- `GET /api/v1/subcontracting/orders`
- `GET /api/v1/subcontracting/orders/{order_id}`
- `POST /api/v1/subcontracting/orders/{order_id}/assign-vendor`
- `POST /api/v1/subcontracting/orders/{order_id}/issue-material`
- `POST /api/v1/subcontracting/orders/{order_id}/record-receipt`
- `GET /api/v1/subcontracting/orders/{order_id}/timeline`

### Non-Goals
- 本轮不做采购单联动
- 本轮不做 routing/MRP orchestration 改写
- 本轮不做制造主服务回写
