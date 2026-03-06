# 开发与验证：并行支线 P2 Breakage Helpdesk Failure Export + Trends + Alert Thresholds

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_EXPORT_TRENDS_ALERT_THRESHOLDS_20260306.md`

## 1. 开发内容

1. 新增 breakage-helpdesk failures 趋势能力：`breakage_helpdesk_failure_trends(...)`。
2. 新增 breakage-helpdesk failures 导出能力：`export_breakage_helpdesk_failures(...)`，支持 `json/csv/md/zip`。
3. `summary/alerts/export_summary/prometheus_metrics` 增加阈值透传：
- `breakage_helpdesk_failed_rate_warn`
- `breakage_helpdesk_failed_total_warn`
4. breakage-helpdesk 失败明细与趋势新增过滤条件：
- `provider_ticket_status`
5. 指标增强：
- `yuantus_parallel_breakage_helpdesk_failed_rate`
- `yuantus_parallel_breakage_helpdesk_failed_by_failure_category{failure_category=...}`
- `yuantus_parallel_breakage_helpdesk_failure_trend_failed_total{bucket_start,bucket_end}`
- `yuantus_parallel_breakage_helpdesk_failure_trend_total_jobs{bucket_start,bucket_end}`
6. 新增 API：
- `GET /api/v1/parallel-ops/breakage-helpdesk/failures/trends`
- `GET /api/v1/parallel-ops/breakage-helpdesk/failures/export`

## 2. 代码清单

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_EXPORT_TRENDS_ALERT_THRESHOLDS_20260306.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_P2_BREAKAGE_HELPDESK_FAILURE_EXPORT_TRENDS_ALERT_THRESHOLDS_20260306.md`

## 3. 验证命令

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k "parallel_ops_overview_summary_and_window_validation"
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py -k "breakage_helpdesk"
pytest -q src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py -k "parallel_ops_endpoints_e2e_with_real_service_data"
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_parallel_tasks_router.py src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py
pytest -q src/yuantus/meta_engine/tests/test_delivery_doc_index_*.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_*.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py
```

## 4. 验证结果

1. `test_parallel_tasks_services.py -k parallel_ops_overview_summary_and_window_validation`
- 结果：`1 passed, 48 deselected`

2. `test_parallel_tasks_router.py -k breakage_helpdesk`
- 结果：`16 passed, 76 deselected`

3. `test_parallel_ops_router_e2e.py -k parallel_ops_endpoints_e2e_with_real_service_data`
- 结果：`1 passed, 7 deselected`

4. 受影响整组回归
- 结果：`153 passed, 0 failed`

5. 文档索引契约测试
- 结果：`13 passed, 0 failed`

## 5. 结论

- 失败导出、趋势、阈值告警与指标扩展已联动完成，且通过 service/router/e2e 与文档契约回归。
