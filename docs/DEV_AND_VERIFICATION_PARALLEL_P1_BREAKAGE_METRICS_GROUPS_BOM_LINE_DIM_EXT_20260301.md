# 开发与验证：并行支线 P1-2 Breakage Metrics BOM 行维度分组扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_METRICS_GROUPS_BOM_LINE_DIM_EXT_20260301.md`

## 1. 本轮开发范围

1. 为 breakage 分组维度新增 `bom_line_item_id`。
2. 让查询与导出路由在参数说明中同步支持该维度。
3. 补齐 service/router/e2e 用例，确保行为可回归。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_METRICS_GROUPS_BOM_LINE_DIM_EXT_20260301.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_PARALLEL_P1_BREAKAGE_METRICS_GROUPS_BOM_LINE_DIM_EXT_20260301.md`
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

1. 目标回归：`70 passed`。
2. 文档索引契约：`2 passed`。
3. `meta_engine` 全量回归：`133 passed, 0 failed`。

## 5. 结论

Breakage 分组能力已覆盖 BOM 行维度，支撑按结构热点定位异常并导出分析。
