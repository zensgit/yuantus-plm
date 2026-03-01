# 开发与验证：并行支线 P1-2 Breakage Incident 导出与 Helpdesk 同步状态扩展

- 日期：2026-03-01
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_INCIDENT_EXPORT_HELPDESK_SYNC_STATUS_EXT_20260301.md`

## 1. 本轮开发范围

1. breakage 事件列表新增 `bom_line_item_id` 过滤，新增事件导出接口。
2. breakage 指标新增 BOM 行聚合字段：
- `by_bom_line_item`
- `top_bom_line_items`
3. helpdesk 同步新增状态查询与结果回写接口，支持回写 `external_ticket_id`。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_INCIDENT_EXPORT_HELPDESK_SYNC_STATUS_EXT_20260301.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_PARALLEL_P1_BREAKAGE_INCIDENT_EXPORT_HELPDESK_SYNC_STATUS_EXT_20260301.md`
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

1. 目标回归：`80 passed, 282 warnings in 9.54s`。
2. 文档索引契约：`2 passed in 0.02s`。
3. `meta_engine` 全量回归：`143 passed, 482 warnings in 15.57s`。

## 5. 结论

Breakage 闭环能力从“统计查询”扩展到“事件导出 + 外部工单状态回写”，可支持问题定位、导出追踪与外部系统对账。
