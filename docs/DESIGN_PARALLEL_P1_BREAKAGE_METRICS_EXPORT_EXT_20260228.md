# 设计文档：并行支线 P1-2 Breakage Metrics 导出扩展

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：在现有 `breakages/metrics` 指标面板基础上，增加 `json/csv/md` 导出能力。

## 1. 目标

1. 支持值班与质量周报对 breakage 指标面板的一键导出。
2. 保持与现有过滤/分页/趋势窗口参数一致，避免双套查询逻辑。
3. 与并行支线既有错误合同保持一致（结构化 `code/message/context`）。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

在 `BreakageIncidentService` 新增：

1. `export_metrics(...)`
- 入参复用 `metrics(...)` 的过滤参数：
  - `status`
  - `severity`
  - `product_item_id`
  - `batch_code`
  - `responsibility`
  - `trend_window_days`
  - `page`
  - `page_size`
- 新增 `export_format`：`json|csv|md`

2. `_metrics_export_rows(metrics)`
- 将 `trend` 序列展开为导出行，并附带全局汇总字段：
  - `total`
  - `repeated_event_count`
  - `repeated_failure_rate`
  - `trend_window_days`
  - 过滤条件回显字段

3. 导出格式定义
- `json`：直接导出完整指标 payload。
- `csv`：导出趋势行（`date/count`）+ 汇总/过滤列。
- `md`：导出摘要（总量、重复率、按维度分布、热点部件）+ 趋势表格。

4. 非法格式
- 抛出 `ValueError("export_format must be json, csv or md")`。

## 2.2 路由层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：
- `GET /api/v1/breakages/metrics/export`

请求参数：
- 与 `GET /api/v1/breakages/metrics` 一致，额外增加：
  - `export_format=json|csv|md`（默认 `json`）

响应：
- `StreamingResponse`
- `Content-Disposition` 下载文件名
- `X-Operator-Id` 透传操作者

错误合同：
- 使用既有错误码 `breakage_metrics_invalid_request`
- `context` 补充 `export_format`

## 3. 兼容性

1. 不涉及数据库迁移。
2. 不改变已有 `GET /breakages/metrics` 行为。
3. 新增接口为只读导出，不影响主流程写路径。

## 4. 风险与回滚

1. 风险
- `md/csv` 导出字段未来扩展时可能影响下游解析。

2. 缓解
- 明确导出字段固定集合，新增字段采用追加策略。

3. 回滚
- 回滚新增导出接口与服务导出方法即可；无 schema 回滚要求。

## 5. 验收标准

1. `json/csv/md` 三种导出格式均可用。
2. 导出支持现有过滤参数并正确反映在内容中。
3. 非法 `export_format` 返回结构化错误合同。
4. 服务层、路由层、E2E 路径均有测试覆盖。
