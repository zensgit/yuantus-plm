# 开发与验证：并行支线 P0 可靠性与错误合同增强

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 对应设计：`/Users/huazhou/Downloads/Github/Yuantus/docs/DESIGN_PARALLEL_P0_RELIABILITY_AND_ERROR_CONTRACT_20260228.md`

## 1. 开发内容

## 1.1 服务层

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`

已完成：
1. `DocumentMultiSiteService`
- 增加同步追踪字段写入。
- 增加幂等冲突计数与最后请求记录。
- 支持 `retry_max_attempts` 参数化重试上限。
- 增加按状态/时间窗口过滤。
- 增加统一同步任务视图 `build_sync_job_view`（含死信判定与重试预算）。

2. `WorkflowCustomActionService`
- 增加规则参数规范化校验（priority/timeout/max_retries）。
- 增加 scope 冲突检测并写入 `conflict_scope`。
- 执行顺序改为确定性排序 `(priority, name, id)`。
- 增加超时控制、重试上限保护。
- 增加标准结果码（`OK/WARN/BLOCK/RETRY_EXHAUSTED`）。

## 1.2 路由层

文件：`/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

已完成：
1. 统一错误结构工具函数：`_error_detail/_raise_api_error/_parse_utc_datetime`。
2. `doc-sync` 路由接入结构化错误与过滤参数。
3. `workflow-actions` 路由接入结构化错误与治理字段输出。
4. `workflow-actions/execute` 返回 `result_code`。

## 1.3 测试

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

新增覆盖：
1. `doc-sync` 幂等冲突、过滤、死信视图。
2. workflow 冲突检测、确定性排序、结果码、超时与重试耗尽。
3. 路由错误合同（`invalid_datetime`、`invalid_workflow_rule`、`workflow_action_execution_failed` 等）。

## 2. 验证命令

1. 目标回归
```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py
```

2. 全量回归
```bash
pytest -q src/yuantus/meta_engine/tests
```

## 3. 验证结果

1. 目标回归：`24 passed`
2. 全量回归：`80 passed, 0 failed`
3. 备注：存在历史 warnings（FastAPI on_event、Pydantic v2 config、httpx app shortcut），本次无新增失败。

## 4. 结论

`P0-1/P0-2/P0-3` 已完成代码落地与测试验证，满足：
1. 同步任务可靠性提升（可观测、可过滤、可诊断）。
2. Workflow 动作治理增强（冲突、排序、超时、重试、标准结果码）。
3. API 错误合同统一（结构化错误码 + 上下文）。

