# 设计文档：并行支线 P0 错误合同统一补强（Extension）

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 目标：将 `parallel_tasks_router` 仍使用裸 `HTTPException(detail=str(...))` 的接口统一为结构化错误合同，降低客户端分支判断复杂度。

## 1. 范围

本次覆盖如下能力域：

1. ECO Activity
2. Consumption Plans
3. Breakage
4. Workorder Document Pack
5. 3D Overlay

不改动数据模型与迁移，不改动成功响应结构。

## 2. 错误合同规范

统一格式：

```json
{
  "detail": {
    "code": "<stable_code>",
    "message": "<human_readable_message>",
    "context": {"...": "..."}
  }
}
```

统一通过 `_raise_api_error(...)` 输出，避免裸字符串 `detail`。

## 3. 接口与错误码映射

1. ECO
- `POST /api/v1/eco-activities`
  - `eco_activity_invalid_request`
- `POST /api/v1/eco-activities/activity/{activity_id}/transition`
  - `eco_activity_not_found` / `eco_activity_blocked` / `eco_activity_transition_invalid`

2. Consumption
- `POST /api/v1/consumption/plans`
  - `consumption_plan_invalid_request`
- `POST /api/v1/consumption/plans/{plan_id}/actuals`
  - `consumption_plan_not_found` / `consumption_actual_invalid_request`
- `GET /api/v1/consumption/plans/{plan_id}/variance`
  - `consumption_plan_not_found`

3. Breakage
- `POST /api/v1/breakages`
  - `breakage_invalid_request`
- `POST /api/v1/breakages/{incident_id}/status`
  - `breakage_not_found` / `breakage_status_invalid`
- `POST /api/v1/breakages/{incident_id}/helpdesk-sync`
  - `breakage_not_found` / `breakage_helpdesk_sync_invalid`

4. Workorder
- `POST /api/v1/workorder-docs/links`
  - `workorder_doc_link_invalid`

5. 3D Overlay
- `POST /api/v1/cad-3d/overlays`
  - `overlay_upsert_invalid`
- `GET /api/v1/cad-3d/overlays/{document_item_id}`
  - `overlay_access_denied` / `overlay_not_found`
- `POST /api/v1/cad-3d/overlays/{document_item_id}/components/resolve-batch`
  - `overlay_access_denied` / `overlay_not_found`
- `GET /api/v1/cad-3d/overlays/{document_item_id}/components/{component_ref}`
  - `overlay_access_denied` / `overlay_not_found`

## 4. 兼容性

1. HTTP 状态码保持语义一致（400/403/404/409）。
2. 失败响应从“字符串 detail”收敛为“结构化 detail”，对依赖 `detail` 字符串的调用方有潜在影响。
3. 为降低影响，`message` 保留原错误文本。

## 5. 风险与回滚

1. 风险
- 少量历史客户端若直接把 `detail` 当字符串解析，需做兼容。

2. 缓解
- 统一新增路由测试断言 `code/context`，确保合同稳定。

3. 回滚
- 仅需回滚 `parallel_tasks_router.py` 与对应测试；无 schema 回滚要求。
