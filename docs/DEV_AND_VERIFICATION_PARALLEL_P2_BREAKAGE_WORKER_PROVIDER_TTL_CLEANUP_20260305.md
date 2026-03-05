# 开发与验证：并行支线 P2 Breakage Worker 执行 + Provider 适配 + 导出 TTL 清理

- 日期：2026-03-05
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P2_BREAKAGE_WORKER_PROVIDER_TTL_CLEANUP_20260305.md`

## 1. 本轮范围

1. Worker 接线 breakage 三类任务（helpdesk/export/cleanup）。
2. Helpdesk provider 适配与错误映射。
3. Export result TTL 清理与 cleanup API。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tasks/breakage_tasks.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/cli.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_breakage_tasks.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_ci_contracts_breakage_worker_handlers.py`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P2_BREAKAGE_WORKER_PROVIDER_TTL_CLEANUP_20260305.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_PARALLEL_P2_BREAKAGE_WORKER_PROVIDER_TTL_CLEANUP_20260305.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DELIVERY_DOC_INDEX.md`

## 3. 验证命令

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py \
  src/yuantus/meta_engine/tests/test_breakage_tasks.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_breakage_worker_handlers.py
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

1. 目标回归：`99 passed, 322 warnings in 10.63s`。
2. 文档索引契约：`2 passed in 0.02s`。
3. `meta_engine` 全量回归：`158 passed, 522 warnings in 17.48s`。

## 5. 结论

本轮将 breakage 从“API 主动执行”推进到“可被 worker 消费的任务闭环”，并引入导出内容生命周期治理，降低长期存储压力并提升运维可控性。
