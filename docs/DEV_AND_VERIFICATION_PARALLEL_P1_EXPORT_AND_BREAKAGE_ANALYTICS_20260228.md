# 开发与验证：并行支线 P1（BOM Delta 导出扩展 + Breakage 指标面板 + Workorder 导出增强）

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 对应设计：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_EXPORT_AND_BREAKAGE_ANALYTICS_20260228.md`

## 1. 本轮开发范围

1. `P1-1` BOM Delta 导出扩展
- `summary.risk_level` 与 `change_summary` 增强。
- `fields` 字段过滤（preview/json/csv 一致）。

2. `P1-2` Breakage 指标面板
- 过滤维度：status/severity/product_item_id/batch_code/responsibility。
- 分页输出：page/page_size/pagination。
- 趋势窗口：7/14/30。

3. `P1-3` Workorder 导出增强
- manifest 增加 `export_meta`、`scope_summary`、`document_scope`。
- PDF 摘要结构升级。
- `workorder` 导出格式错误合同结构化。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/bom_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/bom_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_bom_delta_preview.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

## 3. 验证命令

1. 目标回归
```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py
```

2. 全量回归
```bash
pytest -q src/yuantus/meta_engine/tests
```

## 4. 验证结果

1. 目标回归：`29 passed`
2. 全量回归：`85 passed, 0 failed`
3. 备注：存在历史 warnings（FastAPI on_event、Pydantic v2 config、httpx app shortcut），本次无新增失败。

## 5. 结论

`P1-1/P1-2/P1-3` 已完成落地并通过回归验证，可进入下一批迭代（P2 或 P1 深化）。

