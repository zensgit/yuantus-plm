# 开发与验证：并行支线 P2 ECO Activity SLA Alerts

- 日期：2026-03-05
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`docs/DESIGN_PARALLEL_P2_ECO_ACTIVITY_SLA_ALERTS_20260305.md`

## 1. 本轮开发范围

1. 新增 SLA 告警聚合服务（阈值可配置）。
2. 新增 SLA 告警导出服务（`json/csv/md`）。
3. 新增路由：`/sla/alerts` 与 `/sla/alerts/export`。
4. 增加服务、路由、E2E 测试覆盖。

## 2. 变更文件

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`
- `docs/DESIGN_PARALLEL_P2_ECO_ACTIVITY_SLA_ALERTS_20260305.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_P2_ECO_ACTIVITY_SLA_ALERTS_20260305.md`

## 3. 验证命令

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py
```

## 4. 验证结果

1. 受影响回归：`119 passed, 0 failed`
2. 新增路径覆盖：
- `GET /api/v1/eco-activities/{eco_id}/sla/alerts`
- `GET /api/v1/eco-activities/{eco_id}/sla/alerts/export`

## 5. 结论

ECO 活动 SLA 告警与导出能力已完成并验证，可直接用于质量值班告警看板与日报导出。
