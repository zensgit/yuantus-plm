# 设计文档：并行支线 P2 Breakage Worker 执行 + Provider 适配 + 导出 TTL 清理

- 日期：2026-03-05
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 目标：将 breakage 任务从 API 触发扩展到 Worker 执行链路，并补 provider 适配与导出结果生命周期治理。

## 1. 范围

1. Worker 任务接线：
- `breakage_helpdesk_sync_stub`
- `breakage_incidents_export`
- `breakage_incidents_export_cleanup`

2. Helpdesk provider 适配：
- `stub/jira/zendesk` 票号生成
- provider 错误码映射（timeout/rate/auth/unsupported）
- 与 `failure_category` 归类联动

3. 导出结果 TTL 清理：
- 清理过期 job 的 `export_result.content_b64`
- 标记 `sync_status=expired`
- 关闭下载能力

## 2. 设计

## 2.1 Service 层

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增/增强：
- `run_helpdesk_sync_job(job_id, user_id)`：供 worker 消费 helpdesk 同步任务。
- `_simulate_helpdesk_provider_dispatch(...)`：provider 适配（stub/jira/zendesk）。
- `_map_helpdesk_provider_error(...)`：provider 错误映射。
- `run_incidents_export_job(job_id, user_id)`：worker 消费导出任务。
- `cleanup_expired_incidents_export_results(ttl_hours, limit, user_id)`：导出结果过期清理。

## 2.2 Task 层

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tasks/breakage_tasks.py`

新增 handler：
- `breakage_helpdesk_sync_stub(...)`
- `breakage_incidents_export(...)`
- `breakage_incidents_export_cleanup(...)`

## 2.3 CLI Worker 注册

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/cli.py`

在 `worker` 命令中新增上述 breakage handler 注册，打通实际 worker 执行路径。

## 2.4 Router 清理接口

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增：
- `POST /api/v1/breakages/export/jobs/cleanup`

## 3. 风险与回滚

1. 风险：TTL 清理后下载不可用（符合预期），需调用方理解生命周期。
2. 缓解：状态接口返回 `download_ready=false` 与 `sync_status=expired`。
3. 回滚：移除新增 task/CLI 注册与 cleanup API；无 schema 变更。
