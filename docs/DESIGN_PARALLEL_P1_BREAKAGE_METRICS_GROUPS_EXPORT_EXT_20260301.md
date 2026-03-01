# 设计文档：并行支线 P1-2 Breakage Metrics 分组导出扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：为 breakage 分组指标新增导出能力，支持 `json/csv/md`，并补齐 API 错误合同与验证用例。

## 1. 目标

1. 在现有 `GET /api/v1/breakages/metrics/groups` 基础上补齐导出能力。
2. 导出格式与已有 `breakages/metrics/export` 对齐：`json`、`csv`、`md`。
3. 保持错误语义一致：非法参数统一映射 `breakage_metrics_invalid_request`。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增：

1. `_metrics_groups_export_rows(...)`
- 将 `metrics_groups(...)` 结果展平为导出行。
- 包含字段：`group_by/group_value/count/total_groups/trend_window_days` 与过滤条件。
- 当无分组行时输出默认空行，保证 CSV/Markdown 可导出。

2. `export_metrics_groups(...)`
- 参数复用 `metrics_groups(...)` 并新增 `export_format`。
- `json`：直接导出分组结构。
- `csv`：导出扁平行。
- `md`：输出分组摘要 + 表格。
- 非法格式抛出 `ValueError("export_format must be json, csv or md")`。

## 2.2 路由层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：
- `GET /api/v1/breakages/metrics/groups/export`

行为：
1. 参数与 `groups` 查询接口一致，新增 `export_format`。
2. 响应类型为 `StreamingResponse`。
3. 响应头包含：
- `Content-Disposition`（下载文件名）
- `X-Operator-Id`
4. `ValueError` 映射到：
- `code=breakage_metrics_invalid_request`
- `context` 含 `group_by`、过滤参数、分页、`export_format`。

## 3. 兼容性与风险

1. 兼容性
- 纯新增读接口与 service 方法，不影响现有 breakage 路径。
- 不涉及 DB schema/migration。

2. 风险
- 大分组集合导出体积增大。

3. 缓解
- 复用现有分页参数（默认 `page=1&page_size=20`，上限 200）。

4. 回滚
- 回滚路由与服务导出方法即可，无数据回滚步骤。

## 4. 验收标准

1. `groups/export` 支持 `json/csv/md` 三种格式。
2. 非法 `export_format` 返回结构化错误合同。
3. service/router/e2e 测试覆盖成功与失败路径。
