# 开发与验证：并行支线 P2 Breakage Helpdesk Failure Replay Trends + Cleanup + Replay Alerts

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_TRENDS_CLEANUP_ALERTS_20260306.md`

## 1. 本批次落地内容

1. Replay 趋势接口
- Service: `breakage_helpdesk_replay_trends(...)`
- Router: `GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/trends`

2. Replay 批次清理接口（TTL）
- Service: `cleanup_breakage_helpdesk_failure_replay_batches(...)`
- Router: `POST /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/cleanup`
- 软归档字段：`metadata.replay.archived/archived_at/archive_reason/archive_ttl_hours`

3. Replay SLO 阈值扩展
- `summary/alerts/prometheus_metrics/export_summary` 新增 replay 阈值透传：
  - `breakage_helpdesk_replay_failed_rate_warn`
  - `breakage_helpdesk_replay_failed_total_warn`
  - `breakage_helpdesk_replay_pending_total_warn`
- 新增 hints：`breakage_helpdesk_replay_failed_rate_high`、`breakage_helpdesk_replay_failed_total_high`、`breakage_helpdesk_replay_pending_total_high`
- 新增指标：`yuantus_parallel_breakage_helpdesk_replay_pending_total`

4. Replay 汇总增强
- `summary.breakages.helpdesk` 新增：`replay_pending_jobs`、`replay_by_sync_status`
- replay collector 默认排除 archived 批次。

## 2. 涉及文件

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_TRENDS_CLEANUP_ALERTS_20260306.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_TRENDS_CLEANUP_ALERTS_20260306.md`

## 3. 关键验证命令

1. Service 定向
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k "parallel_ops_overview_summary_and_window_validation or breakage_helpdesk_failure_replay_enqueue_creates_jobs or breakage_helpdesk_failure_replay_batch_not_found"
```
结果：`3 passed`

2. Router 定向
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k "summary_accepts_threshold_overrides or replay_batches_list or replay_trends or replay_batch_export or replay_batches_cleanup"
```
结果：`8 passed`

3. E2E 主链路
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py -k "parallel_ops_endpoints_e2e_with_real_service_data"
```
结果：`1 passed`

4. 三文件回归
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py
```
结果：`173 passed, 0 failed`

## 4. 结论

- replay trends + replay cleanup + replay alerts 阈值链路已完成落地。
- service/router/e2e 已覆盖并验证通过。
- 本批次可作为并行支线完成项进入下阶段。
