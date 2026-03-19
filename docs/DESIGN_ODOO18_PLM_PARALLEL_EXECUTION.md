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
