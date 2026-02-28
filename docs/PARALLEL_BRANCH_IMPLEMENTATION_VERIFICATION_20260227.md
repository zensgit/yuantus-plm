# 并行支线开发验证报告

- 日期：2026-02-27
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 对应实现：P0-A/P0-B/P0-C/P1-D/P1-E/P1-F/P2-G/P2-H

## 1. 验证命令

1. 新增测试定向执行
```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py src/yuantus/meta_engine/tests/test_bom_delta_preview.py
```

2. 关键合同与回归
```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_checkout_external_ref_allowlist_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_checkout_version_baseline_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_checkout_external_repository_allowlist_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py
```

3. 主测试集回归
```bash
pytest -q src/yuantus/meta_engine/tests
```

4. ECO 主流程接入补充验证
```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py
```

5. 接入补充后的主测试集回归
```bash
pytest -q src/yuantus/meta_engine/tests
```

## 2. 验证结果

1. 新增测试
- 结果：`9 passed`
- 结论：并行支线新增服务 + BOM delta 增强功能通过

2. 关键合同与回归
- 结果：`14 passed`
- 结论：migration 表覆盖合同、近期 workflow 合同与新增功能测试兼容

3. 主测试集
- 结果：`65 passed, 0 failed`
- 耗时：`10.62s`
- 备注：存在历史 warning（FastAPI on_event、Pydantic v2 config、httpx app shortcut 等），本次无新增失败

4. ECO 主流程接入补充验证
- 结果：`11 passed`
- 结论：`move_to_stage` / `action_apply` 已接入活动网关与自定义动作 hooks，行为符合预期

5. 接入补充后主测试集
- 结果：`67 passed, 0 failed`
- 耗时：`8.33s`
- 备注：warnings 类型与此前一致，无新增失败

## 3. 关键落地项核对

1. Schema 与迁移
- 新模型：`src/yuantus/meta_engine/models/parallel_tasks.py`
- 新迁移：`migrations/versions/z1b2c3d4e7a5_add_parallel_branch_tables.py`
- 结论：通过 migration coverage 合同校验

2. 服务层
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- 覆盖：doc-sync / eco-activity / workflow-actions / consumption / breakage / workorder-doc / 3d-overlay

3. API 层
- 新路由：`src/yuantus/meta_engine/web/parallel_tasks_router.py`
- 主应用接入：`src/yuantus/api/app.py`

4. BOM 增强
- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- 新增 delta 预览与导出（json/csv）

5. 新增测试
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_bom_delta_preview.py`
- `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`

## 4. 结论

并行支线清单对应能力已完成最小可交付实现，且通过本地新增测试、关键合同测试与主测试集回归验证，可进入后续联调与分批合并阶段。
