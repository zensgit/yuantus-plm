# 设计文档：并行支线 P1（BOM Delta 导出扩展 + Breakage 指标面板 + Workorder 导出增强）

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：`P1-1 + P1-2 + P1-3`

## 1. 目标

1. BOM Delta 导出支持风险摘要与字段过滤，提升评审效率。
2. Breakage 指标面板支持维度过滤、分页和趋势窗口（7/14/30 天）。
3. Workorder 文档导出增强 PDF 可读性与导出元信息一致性，统一 `zip/json/pdf` 行为。

## 2. 方案设计

## 2.1 P1-1 BOM Delta 导出扩展

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/bom_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/bom_router.py`

### 关键设计

1. 在 delta preview 增加结构化摘要：
- `summary.risk_level`
- `change_summary.ops`（adds/removes/updates/structural）
- `change_summary.severity`（major/minor/info）

2. 增加导出字段白名单：
- `op,line_key,parent_id,child_id,relationship_id,severity,risk_level,change_count,field,before,after,properties`
- 非法字段直接报 `400`。

3. preview/export 一致化：
- `GET /compare/delta/preview` 支持 `fields`，返回 `selected_fields`。
- `GET /compare/delta/export` 的 `json/csv` 均基于同一字段过滤规则。

## 2.2 P1-2 Breakage 指标面板 API

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

### 关键设计

1. 过滤维度：
- `status`
- `severity`
- `product_item_id`
- `batch_code`
- `responsibility`

2. 趋势窗口：
- `trend_window_days` 仅允许 `7|14|30`。

3. 分页：
- `page/page_size`（page_size 上限 200）
- 返回 `pagination` 与当前页 `incidents`。

4. 指标扩展：
- `by_responsibility`
- `trend`（按日序列）
- `filters`（回显请求条件）

## 2.3 P1-3 Workorder 导出增强

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

### 关键设计

1. 导出元信息统一写入 manifest：
- `export_meta.generated_at`
- `export_meta.job_no`
- `export_meta.operator_id`
- `export_meta.operator_name`
- `export_meta.exported_by`
- `export_meta.format_version`

2. 文档分类：
- 文档新增 `document_scope`（`routing|operation`）
- manifest 增加 `scope_summary`

3. PDF 摘要增强：
- 显示 Export Metadata、Document Summary、Documents 三段
- 包含 scope、继承、可见性等信息

4. 错误合同统一：
- `workorder` 导出格式错误返回结构化错误：`workorder_export_invalid_format`

## 3. 兼容与风险

1. 不新增数据库迁移，所有新增信息由 manifest/payload 承载。
2. 默认不传 `fields` 时行为与旧版本兼容。
3. Breakage 过滤在服务层进行，确保 SQLite 与 PG 行为一致。

## 4. 验收标准

1. BOM delta：`preview/json/csv` 字段过滤一致，摘要统计与操作数一致。
2. Breakage：过滤+分页+趋势输出稳定，非法窗口返回 400。
3. Workorder：`zip/json/pdf` 均携带一致 `export_meta`，PDF 摘要可读。

