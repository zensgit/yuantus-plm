# 开发与验证：并行支线 P1-2 Breakage Metrics BOM 行过滤扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_METRICS_BOM_LINE_FILTER_EXT_20260301.md`

## 1. 本轮开发范围

1. 为 breakage 指标查询与导出能力增加 `bom_line_item_id` 过滤参数。
2. 补齐 service/router/e2e 回归，验证过滤参数端到端透传。
3. 更新交付索引，纳入本轮验证文档。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_METRICS_BOM_LINE_FILTER_EXT_20260301.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_PARALLEL_P1_BREAKAGE_METRICS_BOM_LINE_FILTER_EXT_20260301.md`
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

Breakage 指标链路已支持 BOM 行级过滤，能够更精确定位结构热点并输出带过滤上下文的分析导出结果。
