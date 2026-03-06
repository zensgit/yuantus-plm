# 设计文档：并行支线 P2 Breakage Helpdesk Failure Export + Trends + Alert Thresholds

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 参考：`references/odoo18-enterprise-main/addons/plm_breakages`、`references/odoo18-enterprise-main/addons/plm_ent_breakages_helpdesk`

## 1. 目标

1. 为 breakage-helpdesk 失败排障补齐导出能力（`json/csv/md/zip`），支持离线分析与审计。
2. 提供失败趋势接口，支持按时间桶观察失败变化。
3. 为并行运维总览增加 breakage-helpdesk 失败阈值告警（rate/total），实现可配置预警。
4. 增强 breakage-helpdesk 失败过滤维度（`provider_ticket_status`）与 Prometheus 指标可观测性。

## 2. 范围

- Service 增强：
  - `breakage_helpdesk_failure_trends(...)`
  - `export_breakage_helpdesk_failures(...)`
  - `summary/alerts/export_summary/prometheus_metrics` 新阈值透传
- Router 增强：
  - `GET /api/v1/parallel-ops/breakage-helpdesk/failures/trends`
  - `GET /api/v1/parallel-ops/breakage-helpdesk/failures/export`
  - 现有 `summary/alerts/summary/export/metrics` 增加新阈值 query 参数
- Tests：service/router/e2e 覆盖

## 3. 设计要点

### 3.1 失败趋势

- 时间参数：`window_days` + `bucket_days`（复用现有 bucket 约束）。
- 过滤参数：`provider`、`failure_category`、`provider_ticket_status`。
- 输出：
  - `points[]`：`total_jobs`、`failed_jobs`、`failed_rate`、`by_failure_category`
  - `aggregates`：窗口总量与失败率

### 3.2 失败导出

- 基于 failure 明细统一结构导出：
  - `json`：完整 payload
  - `csv`：结构化列
  - `md`：值班可读表格
  - `zip`：包含 `failures.json`、`failures.csv`、`summary.md`
- 导出错误合同：`export_format must be json, csv, md or zip`
- 输出补充聚合：
  - `by_provider_ticket_status`

### 3.3 告警阈值扩展

- 新增阈值（默认值）：
  - `breakage_helpdesk_failed_rate_warn` = `0.5`
  - `breakage_helpdesk_failed_total_warn` = `5`
- 新增 hint code：
  - `breakage_helpdesk_failed_rate_high`
  - `breakage_helpdesk_failed_total_high`
- 阈值接入：`summary`、`alerts`、`summary/export`、`metrics`

### 3.4 指标扩展

- 新增总体失败率指标：
  - `yuantus_parallel_breakage_helpdesk_failed_rate`
- 新增按失败分类失败数：
  - `yuantus_parallel_breakage_helpdesk_failed_by_failure_category{failure_category=...}`
- 新增趋势桶指标：
  - `yuantus_parallel_breakage_helpdesk_failure_trend_failed_total{bucket_start,bucket_end}`
  - `yuantus_parallel_breakage_helpdesk_failure_trend_total_jobs{bucket_start,bucket_end}`

## 4. 兼容性

1. 新接口为增量接口，不影响既有调用。
2. 新阈值参数均为可选，旧调用路径无需修改。
3. 旧数据字段缺失时回退为 `unknown`，避免运行时失败。

## 5. 风险与缓解

1. 风险：失败分类字段在历史数据中不完整。
- 缓解：统一回退 `unknown` 分类，保证趋势/导出稳定。

2. 风险：低阈值导致误报警。
- 缓解：阈值可配置并在 API 层透传；默认阈值保持保守。

## 6. 验收标准

1. failures 可导出 `json/csv/md/zip`。
2. 趋势接口支持 provider/failure_category/provider_ticket_status 过滤与聚合。
3. summary/alerts 可通过新阈值触发与抑制 helpdesk 失败告警。
4. Prometheus 输出包含 helpdesk 失败率、失败分类、趋势桶指标。
5. service/router/e2e 与文档契约测试通过。
