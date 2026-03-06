# 开发与验证：并行支线 P2 Breakage Helpdesk Failure Replay Batch List + Export + Replay Metrics

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_BATCH_LIST_EXPORT_20260306.md`

## 1. 本批次开发落地

1. Service replay 批次能力
- 新增 replay rows 收敛函数：`_collect_breakage_helpdesk_replay_rows(...)`。
- 新增批次列表：`list_breakage_helpdesk_failure_replay_batches(...)`。
- 新增批次导出：`export_breakage_helpdesk_failure_replay_batch(...)`。
- 既有 `get_breakage_helpdesk_failure_replay_batch(...)` 重构为复用 collector。

2. Service replay 可观测字段
- `summary.breakages.helpdesk` 新增 replay 字段（jobs/batches/failed/rate/by_job_status/by_provider）。
- `prometheus_metrics()` 新增 replay 系列指标。
- `summary export` 新增 replay 统计行。

3. Router 接口新增
- `GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches`
- `GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}/export`
- 错误合同映射：
  - 参数非法 -> `parallel_ops_invalid_request`
  - 批次不存在 -> `parallel_ops_replay_batch_not_found`

4. Tests 扩展
- service：新增批次列表/导出断言与 replay 指标断言。
- router：新增批次列表与导出路由单测。
- e2e：新增 replay 批次列表、批次导出、replay summary 与 replay metrics 断言。

## 2. 涉及文件

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_BATCH_LIST_EXPORT_20260306.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_BATCH_LIST_EXPORT_20260306.md`

## 3. 验证命令与结果

1. Service replay 定向
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k "replay or breakage_helpdesk_summary or prometheus_metrics"
```
结果：`5 passed, 49 deselected`

2. Router replay 定向
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k "replay_batches_list or replay_batch_export"
```
结果：`3 passed, 104 deselected`

3. E2E 主链路定向
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py -k "parallel_ops_endpoints_e2e_with_real_service_data"
```
结果：`1 passed, 7 deselected`

4. E2E 全文件回归
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py
```
结果：`8 passed, 0 failed`

## 4. 结论

- replay 批次列表与导出能力已落地。
- replay 统计已打通到 summary / metrics / summary-export。
- service/router/e2e 覆盖均通过，当前批次可交付。
