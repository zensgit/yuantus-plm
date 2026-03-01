# 开发与验证：并行支线 P2 Breakage Helpdesk 执行器 + 导出任务化 + Cockpit 聚合

- 日期：2026-03-02
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_EXECUTOR_EXPORT_JOB_COCKPIT_20260302.md`

## 1. 本轮范围

1. Helpdesk 同步执行器：execute 接口 + 失败分类 + idempotency/retry 增强。
2. Breakage 导出任务化：创建任务、查状态、下载结果。
3. Breakage cockpit 聚合与导出：`incidents + metrics + helpdesk_sync_summary`。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P2_BREAKAGE_HELPDESK_EXECUTOR_EXPORT_JOB_COCKPIT_20260302.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_PARALLEL_P2_BREAKAGE_HELPDESK_EXECUTOR_EXPORT_JOB_COCKPIT_20260302.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DELIVERY_DOC_INDEX.md`

## 3. 验证命令

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py
```

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

```bash
pytest -q src/yuantus/meta_engine/tests
```

## 4. 验证结果

1. 目标回归：`90 passed, 312 warnings in 9.33s`。
2. 文档索引契约：`2 passed in 0.03s`。
3. `meta_engine` 全量回归：`153 passed, 512 warnings in 15.35s`。

## 5. 结论

本轮将 breakage 能力从“指标+列表+手工回写”扩展到“可执行同步、任务化导出、cockpit 聚合”，可支撑更稳定的外部对账与可观测运营闭环。
