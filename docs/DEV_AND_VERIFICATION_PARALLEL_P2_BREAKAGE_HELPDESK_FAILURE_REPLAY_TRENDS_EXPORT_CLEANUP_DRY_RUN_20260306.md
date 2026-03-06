# 开发与验证：并行支线 P2 Breakage Helpdesk Failure Replay Trends Export + Cleanup Dry-Run

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_TRENDS_EXPORT_CLEANUP_DRY_RUN_20260306.md`

## 1. 本批次开发

1. Replay trends export
- Service 新增：`export_breakage_helpdesk_replay_trends(...)`
- Router 新增：`GET /api/v1/parallel-ops/breakage-helpdesk/failures/replay/trends/export`

2. Replay cleanup dry-run
- Service 扩展：`cleanup_breakage_helpdesk_failure_replay_batches(..., dry_run=False)`
- Router 扩展：`ParallelOpsBreakageHelpdeskFailureReplayCleanupRequest` 新增 `dry_run`

3. 测试覆盖
- service：新增 replay trends export、cleanup dry-run 行为验证
- router：新增 replay trends export 下载与 invalid 合同测试；cleanup dry-run 透传验证
- e2e：新增 replay trends export 与 cleanup dry-run 集成验证

## 2. 涉及文件

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_TRENDS_EXPORT_CLEANUP_DRY_RUN_20260306.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_REPLAY_TRENDS_EXPORT_CLEANUP_DRY_RUN_20260306.md`

## 3. 验证命令与结果

1. service 定向
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k "parallel_ops_overview_summary_and_window_validation or breakage_helpdesk_failure_replay_enqueue_creates_jobs or breakage_helpdesk_failure_replay_batch_not_found"
```
结果：`3 passed`

2. router 定向
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k "summary_accepts_threshold_overrides or replay_trends or replay_batches_cleanup"
```
结果：`7 passed`

3. e2e 定向
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py -k "parallel_ops_endpoints_e2e_with_real_service_data"
```
结果：`1 passed`

4. 受影响回归
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py src/yuantus/meta_engine/tests/test_breakage_tasks.py src/yuantus/meta_engine/tests/test_ci_contracts_breakage_worker_handlers.py src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py
```
结果：`184 passed, 0 failed`

5. 文档索引契约
```bash
pytest -q src/yuantus/meta_engine/tests/test_delivery_doc_index_*.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_*.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py
```
结果：`13 passed`

## 4. 结论

- replay trends export 与 cleanup dry-run 已完成交付并通过回归。
- 当前 replay 支线具备查询、导出、趋势、清理、告警的完整运维闭环。
