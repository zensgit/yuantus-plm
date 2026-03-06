# 开发与验证：并行支线 P2 Breakage Helpdesk Failure Triage + Replay + Export Ops

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_TRIAGE_ENDPOINT_20260306.md`

## 1. 本批次新增开发

1. replay 入队能力
- 新增 `enqueue_breakage_helpdesk_failure_replay_jobs(...)`（按 `job_ids` 或过滤条件选择失败 job 入队重放）。
- 新增路由：`POST /api/v1/parallel-ops/breakage-helpdesk/failures/replay/enqueue`。
- replay 元数据新增 `batch_id`，支持后续批次追踪。

2. replay 批次状态查询
- 新增 `get_breakage_helpdesk_failure_replay_batch(...)`。
- 新增路由：`GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}`。

3. export jobs 概览能力
- 新增 `breakage_helpdesk_failures_export_jobs_overview(...)`（`by_job_status/by_sync_status/by_provider/by_failure_category/by_export_format` 聚合）。
- 新增 `duration_seconds`（`count/min/max/avg/p50/p95`）统计与 `failure_category` 过滤。
- 新增路由：`GET /api/v1/parallel-ops/breakage-helpdesk/failures/export/jobs/overview`。

4. provider 失败预算告警与指标
- 新增阈值：
  - `breakage_helpdesk_provider_failed_rate_warn`
  - `breakage_helpdesk_provider_failed_min_jobs_warn`
  - `breakage_helpdesk_provider_failed_rate_critical`
  - `breakage_helpdesk_provider_failed_min_jobs_critical`
- 新增 hint：`breakage_helpdesk_provider_failed_rate_high`
- 新增 hint：`breakage_helpdesk_provider_failed_rate_critical`
- 新增 metrics：
  - `yuantus_parallel_breakage_helpdesk_provider_failed_total{provider=...}`
  - `yuantus_parallel_breakage_helpdesk_provider_failed_rate{provider=...}`
- `summary/alerts/metrics/export_summary` 均已接入 `warn+critical` 阈值透传与输出。

## 2. 涉及文件

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_TRIAGE_ENDPOINT_20260306.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_TRIAGE_ENDPOINT_20260306.md`

## 3. 关键验证命令

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k "parallel_ops_overview_summary_and_window_validation or breakage_helpdesk_failure_replay_enqueue_creates_jobs or breakage_helpdesk_failure_replay_batch_not_found or breakage_helpdesk_export_jobs_overview_returns_aggregates or breakage_helpdesk_failure_triage_apply_persists_payload or breakage_helpdesk_failures_export_job_lifecycle_and_cleanup"
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k "parallel_ops_summary_accepts_threshold_overrides or replay_enqueue or replay_batch or export_jobs_overview or breakage_helpdesk and (triage or export_job or failures_export or failure_trends or failures_returns_payload)"
pytest -q src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py -k "parallel_ops_endpoints_e2e_with_real_service_data"
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py src/yuantus/meta_engine/tests/test_breakage_tasks.py src/yuantus/meta_engine/tests/test_ci_contracts_breakage_worker_handlers.py src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py
pytest -q src/yuantus/meta_engine/tests/test_delivery_doc_index_*.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_*.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py
```

## 4. 验证结果

1. service 定向：`6 passed, 48 deselected`
2. router 定向：`21 passed, 83 deselected`
3. e2e 定向：`1 passed, 7 deselected`
4. 受影响整组回归：`175 passed, 0 failed`
5. 文档索引契约：`13 passed, 0 failed`

## 5. 本批次修复点

1. 修复 `summary()` 阈值参数重复插入导致的签名污染。
2. 修复 replay invalid 测试场景（避免被 Pydantic 422 提前拦截，改为 service 层 400 合同验证）。
3. 新增 replay batch 状态查询与 404 错误合同映射。
4. 新增 export overview `failure_category` 聚合与耗时统计。
5. 补齐 provider critical 阈值在 `summary/alerts/metrics/export_summary` 的透传链路。

## 6. 结论

- replay 入队 + 批次状态、export jobs 概览增强、provider 失败预算（warn+critical）已落地并通过代码回归。
- 当前并行支线在受影响范围内验证全绿，可继续推进下一批功能。
