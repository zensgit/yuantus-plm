# 开发与验证：并行支线 P1-2 Breakage Metrics 导出扩展

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_METRICS_EXPORT_EXT_20260228.md`

## 1. 本轮开发范围

1. 服务层新增 `BreakageIncidentService.export_metrics(...)`，支持 `json/csv/md`。
2. 路由层新增 `GET /api/v1/breakages/metrics/export`。
3. 错误合同统一沿用 `breakage_metrics_invalid_request`，补齐 `export_format` 上下文。
4. 增加服务、路由与真实服务路径 E2E 测试。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P1_BREAKAGE_METRICS_EXPORT_EXT_20260228.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_PARALLEL_P1_BREAKAGE_METRICS_EXPORT_EXT_20260228.md`
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

1. 目标回归：`60 passed`
2. `meta_engine` 全量回归：`121 passed, 0 failed`

## 5. 结论

`breakage metrics` 导出扩展已完成并通过回归，满足 `json/csv/md` 导出与错误合同要求，可继续进入下一条并行支线迭代。
