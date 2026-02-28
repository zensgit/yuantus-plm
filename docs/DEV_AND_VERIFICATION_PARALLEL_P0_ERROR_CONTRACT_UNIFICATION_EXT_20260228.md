# 开发与验证：并行支线 P0 错误合同统一补强（Extension）

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P0_ERROR_CONTRACT_UNIFICATION_EXT_20260228.md`

## 1. 本轮变更

1. 将 `parallel_tasks_router.py` 中剩余裸 `HTTPException(detail=str(...))` 路径统一为 `_raise_api_error`。
2. 为 ECO/Consumption/Breakage/Workorder/3D Overlay 补齐稳定错误码与上下文字段。
3. 扩展 `test_parallel_tasks_router.py`，新增错误合同断言用例。

## 2. 变更文件

- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P0_ERROR_CONTRACT_UNIFICATION_EXT_20260228.md`
- `/Users/huazhou/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_PARALLEL_P0_ERROR_CONTRACT_UNIFICATION_EXT_20260228.md`

## 3. 验证命令

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py
```

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

1. 路由合同测试：`40 passed`
2. 并行支线目标回归：`56 passed`
3. `meta_engine` 全量回归：`117 passed, 0 failed`

## 5. 结论

本轮完成并行支线路由错误合同统一补强，错误码/上下文字段可稳定用于客户端与运维排障，且未引入回归失败。
