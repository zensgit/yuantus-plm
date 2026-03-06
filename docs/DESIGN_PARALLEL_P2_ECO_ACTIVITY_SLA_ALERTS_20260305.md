# 设计文档：并行支线 P2 ECO Activity SLA Alerts

- 日期：2026-03-05
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：在 ECO 活动 SLA 视图基础上新增告警判定与导出能力。

## 1. 目标

1. 提供可配置阈值的 SLA 告警（逾期率、临期数量、阻塞逾期）。
2. 保持与既有 SLA 查询语义一致（时间窗口、过滤条件可复用）。
3. 支持 `json/csv/md` 导出，用于值班群播报和日报归档。

## 2. 方案

## 2.1 服务层

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

在 `ECOActivityValidationService` 新增：

1. `activity_sla_alerts(...)`
- 基于 `activity_sla(...)` 输出构建告警。
- 阈值参数：
  - `overdue_rate_warn`
  - `due_soon_count_warn`
  - `blocking_overdue_warn`
- 输出：`status/alerts/overview/operator context`。

2. `export_activity_sla_alerts(...)`
- 支持 `json/csv/md`。
- `csv`：告警列表 + 核心指标列。
- `md`：摘要与告警表格。

3. 阈值归一化
- `_normalize_alert_rate_threshold(...)`
- `_normalize_alert_count_threshold(...)`

## 2.2 路由层

文件：`src/yuantus/meta_engine/web/parallel_tasks_router.py`

新增接口：

1. `GET /api/v1/eco-activities/{eco_id}/sla/alerts`
2. `GET /api/v1/eco-activities/{eco_id}/sla/alerts/export`

错误合同：
- `eco_activity_sla_alerts_invalid`
- `eco_activity_sla_alerts_export_invalid`

## 3. 兼容性

1. 无 schema 变更。
2. 不改变原 `GET /eco-activities/{eco_id}/sla` 行为。
3. 新能力作为扩展查询/导出路径，兼容现有调用方。

## 4. 风险与缓解

1. 风险：阈值设置过敏导致告警泛滥。
2. 缓解：提供显式阈值参数并在路由层暴露可调默认值。
3. 风险：导出字段定义与消费脚本耦合。
4. 缓解：采用稳定列定义，新增字段仅追加。

## 5. 验收标准

1. 三类 SLA 告警可按阈值触发。
2. `alerts` 与 `overview` 数据一致。
3. 导出 `json/csv/md` 三格式可用。
4. 服务层、路由层、E2E 测试通过。
