# 设计文档：并行支线 P1-2 Breakage Incident 导出与 Helpdesk 同步状态扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 参考：
  - `/Users/huazhou/Downloads/Github/Yuantus/references/odoo18-enterprise-main/addons/plm_breakages/models/mrp_bom.py`
  - `/Users/huazhou/Downloads/Github/Yuantus/references/odoo18-enterprise-main/addons/plm_breakages/models/product_product.py`
- 范围：补齐 breakage 事件导出、指标 BOM 行 TopN 聚合，以及 helpdesk 同步状态闭环接口。

## 1. 目标

1. 补齐事件列表导出能力，支持按 BOM 行过滤回溯问题单。
2. 在指标接口中增加 `bom_line_item_id` 聚合视图（`by_*` + `top_*`）。
3. 新增 helpdesk 同步状态查询与结果回写接口，提升重试与闭环可观测性。

## 2. 方案

## 2.1 服务层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增与增强：

1. `list_incidents(...)` 新增 `bom_line_item_id` 过滤透传。
2. 新增 `export_incidents(...)`：
- 支持 `json/csv/md`
- 支持 `page/page_size`
- 支持过滤条件透传（含 `bom_line_item_id_filter`）。
3. 指标聚合增强：
- 新增 `by_bom_line_item`
- 新增 `top_bom_line_items`
- Markdown 导出同步展示。
4. Helpdesk 同步闭环：
- 新增 `get_helpdesk_sync_status(incident_id)`
- 新增 `record_helpdesk_sync_result(...)`
- 新增内部 job 视图构建与 incident-job 关联解析。
- `enqueue_helpdesk_stub_sync(...)` 初始 payload 增加 `helpdesk_sync.sync_status=queued` 与 BOM 行信息。

## 2.2 路由层

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：

1. `GET /api/v1/breakages/export`
- 导出事件明细（`json/csv/md`）。

2. `GET /api/v1/breakages/{incident_id}/helpdesk-sync/status`
- 查询 incident 的 helpdesk 同步状态和历史 job。

3. `POST /api/v1/breakages/{incident_id}/helpdesk-sync/result`
- 回写同步结果（`completed|failed`），可附 `external_ticket_id`。

改造接口：

1. `GET /api/v1/breakages` 新增 `bom_line_item_id` 过滤参数。

错误合同：
- 导出事件参数错误：`breakage_invalid_request`
- helpdesk 结果参数错误：`breakage_helpdesk_sync_invalid`
- incident 不存在：`breakage_not_found`

## 3. 兼容性

1. 全为增量能力，既有接口默认行为保持兼容。
2. 不新增数据库表，复用 `meta_conversion_jobs` payload 承载同步回写字段。

## 4. 风险与回滚

1. 风险
- 同步状态依赖 `payload` 结构，外部 worker 若不更新字段，会回退为 job 状态视图。

2. 缓解
- 视图层同时读取 `job.status` 与 `payload.helpdesk_sync/result`，保证降级可用。

3. 回滚
- 下线新增路由并删除新增 service 方法即可，无 schema 回滚步骤。

## 5. 验收标准

1. `breakages/export` 可按 BOM 行过滤并导出三种格式。
2. `breakages/metrics` 返回 `by_bom_line_item` 与 `top_bom_line_items`。
3. helpdesk 同步状态可查询，结果可回写并附带 `external_ticket_id`。
4. service/router/e2e 与全量回归通过。
