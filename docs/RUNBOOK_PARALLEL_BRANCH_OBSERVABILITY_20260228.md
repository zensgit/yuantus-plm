# Runbook：Parallel Branch 观测与值班处置

- 日期：2026-02-28
- 适用仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 适用范围：并行支线 `Consumption Template` / `3D Overlay` / `Breakage` 相关 API

## 1. SLI/SLO 建议

## 1.1 3D Overlay 查询

- SLI：`overlay_cache_hit_rate = hits / (hits + misses)`
- 目标：`>= 0.80`（5 分钟窗口）
- SLI：`overlay_cache_evictions_per_5m`
- 目标：`<= 20`
- SLI：`overlay_batch_resolve_p95_ms`
- 目标：`<= 250ms`

## 1.2 Consumption Template

- SLI：`template_version_activation_success_rate`
- 目标：`>= 99.5%`
- SLI：`template_impact_preview_error_rate`
- 目标：`<= 0.5%`

## 1.3 Breakage Metrics（联动可视化）

- SLI：`breakage_metrics_api_error_rate`
- 目标：`<= 1%`
- SLI：`breakage_metrics_p95_ms`
- 目标：`<= 400ms`

## 2. 日常巡检

1. 调用 `GET /api/v1/cad-3d/overlays/cache/stats`，记录 `hits/misses/evictions/entries`。
2. 抽样调用 `POST /api/v1/cad-3d/overlays/{document_item_id}/components/resolve-batch`，核对单条回查一致性。
3. 抽样调用模板接口：
- `GET /api/v1/consumption/templates/{template_key}/versions`
- `POST /api/v1/consumption/templates/{template_key}/impact-preview`
4. 检查失败请求日志，确认错误码是否落在合同范围。

## 3. 故障处置

## 3.1 Overlay 查询延迟突增

1. 观察 `cache/stats`：若 `misses` 快速上升且 `entries` 持续低位，判定缓存未生效。
2. 核查是否有高频 `upsert_overlay` 导致持续失效。
3. 临时措施：
- 前端改用批量回查，减少单条往返次数。
- 降低非关键请求并发。
4. 持续异常时执行版本回退（见第 5 节）。

## 3.2 模板版本激活失败

1. 调用 `POST /api/v1/consumption/templates/versions/{plan_id}/state` 复现并记录 `detail.code`。
2. 若为 `consumption_template_version_not_found`：检查 `plan_id` 是否来自模板列表接口。
3. 若为 `consumption_template_version_invalid`：检查目标 plan 是否模板版本数据。
4. 恢复策略：先切回上一活动版本，再排查异常版本元信息。

## 3.3 影响预览异常

1. 调用 `POST /api/v1/consumption/templates/{template_key}/impact-preview`，比对 `active_version` 与 `versions` 列表。
2. 若 `active_version` 缺失：先确认该模板是否存在激活版本。
3. 记录 `summary.baseline_quantity` 与活动版本计划量是否一致。

## 4. 演练记录模板

- 演练时间：
- 故障场景：
- 检测方式（SLI/告警）：
- 处置步骤：
- 恢复时间：
- 复盘结论：

## 5. 回滚路径

1. 应用层回滚到前一版本（不包含 P2 新接口）。
2. 对外降级：
- 停用批量回查入口，改用单条 `components/{component_ref}`。
- 暂停模板版本切换入口，仅保留历史查询。
3. 数据层：无需 schema 回滚；`ConsumptionPlan` 与 `ThreeDOverlay` 结构不变。
