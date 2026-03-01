# 开发与验证：并行支线 P1-2 Breakage Metrics 分组查询扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_METRICS_GROUPS_QUERY_EXT_20260301.md`

## 1. 本轮开发范围

1. 新增 `BreakageIncidentService.metrics_groups(...)`（分组 + 分页）。
2. 新增 API：`GET /api/v1/breakages/metrics/groups`。
3. 补齐错误合同映射与测试。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_METRICS_GROUPS_QUERY_EXT_20260301.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_PARALLEL_P1_BREAKAGE_METRICS_GROUPS_QUERY_EXT_20260301.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DELIVERY_DOC_INDEX.md`

## 3. 验证命令

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py
```

```bash
pytest -q src/yuantus/meta_engine/tests
```

## 4. 验证结果

1. 目标回归：`65 passed`
2. `meta_engine` 全量回归：`122 passed, 0 failed`

## 5. 结论

Breakage 指标分组查询能力已交付，支持产品/批次/责任三维聚合分页查询，并通过回归验证。
