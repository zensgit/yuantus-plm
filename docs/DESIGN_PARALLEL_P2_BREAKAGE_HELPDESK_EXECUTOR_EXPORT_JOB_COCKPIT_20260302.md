# 设计文档：并行支线 P2 Breakage Helpdesk 执行器 + 导出任务化 + Cockpit 聚合

- 日期：2026-03-02
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 参考：
  - `/Users/huazhou/Downloads/Github/Yuantus/references/odoo18-enterprise-main/addons/plm_breakages/models/mrp_bom.py`
  - `/Users/huazhou/Downloads/Github/Yuantus/references/odoo18-enterprise-main/addons/plm_breakages/models/product_product.py`

## 1. 目标

1. 将 helpdesk 同步从“仅入队+回写”扩展为“可执行”闭环，增强重试和失败分类可观测性。
2. 将 breakage 事件导出扩展为任务化接口，支持异步查询状态与下载。
3. 提供 breakage cockpit 聚合接口，减少前端多接口拼装成本。

## 2. 方案概览

## 2.1 Helpdesk 执行器

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

- 增强 `enqueue_helpdesk_stub_sync(...)`：
  - 支持 `provider`、`idempotency_key`、`retry_max_attempts`。
  - 入队 payload 写入 `integration` 与扩展 `helpdesk_sync` 字段。
  - 当传入 `idempotency_key` 时，dedupe key 使用稳定 idempotency 语义。
- 新增 `execute_helpdesk_sync(...)`：
  - 支持 `simulate_status=completed|failed`。
  - 同步更新 `attempt_count/started_at/completed_at/status`。
  - failed 场景计算 `failure_category=transient|permanent|unknown`。
- 扩展 `record_helpdesk_sync_result(...)`：
  - 支持 `error_code` 与失败分类。
- 新增路由：
  - `POST /api/v1/breakages/{incident_id}/helpdesk-sync/execute`

## 2.2 Breakage 导出任务化

- 新增任务类型：`breakage_incidents_export`（复用 `meta_conversion_jobs`）
- 新增 service 能力：
  - `enqueue_incidents_export_job(...)`
  - `execute_incidents_export_job(...)`
  - `get_incidents_export_job(...)`
  - `download_incidents_export_job(...)`
- 新增路由：
  - `POST /api/v1/breakages/export/jobs`
  - `GET /api/v1/breakages/export/jobs/{job_id}`
  - `GET /api/v1/breakages/export/jobs/{job_id}/download`

## 2.3 Breakage Cockpit 聚合

- 新增 service：
  - `cockpit(...)`：聚合 `incidents + metrics + helpdesk_sync_summary`
  - `export_cockpit(...)`：支持 `json|csv|md`
- 新增路由：
  - `GET /api/v1/breakages/cockpit`
  - `GET /api/v1/breakages/cockpit/export`

## 3. 错误合同

- `breakage_helpdesk_sync_invalid`
- `breakage_export_job_invalid`
- `breakage_export_job_not_found`
- `breakage_cockpit_invalid_request`

## 4. 兼容性与回滚

1. 均为增量能力，原有 breakage API 不移除不破坏。
2. 不引入新表，复用 `meta_conversion_jobs` 持久化导出任务结果和 helpdesk 同步上下文。
3. 回滚可通过下线新增路由与服务方法完成，无 schema 回滚。
