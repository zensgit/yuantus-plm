# C14 Approvals Export Ops-Report Bootstrap Design

## Goal
- 在现有 `approvals` bootstrap 上补齐读侧导出和 bootstrap diagnostics。

## Scope
- `GET /api/v1/approvals/requests/export`
- `GET /api/v1/approvals/summary/export`
- `GET /api/v1/approvals/ops-report`
- `GET /api/v1/approvals/ops-report/export`

## Defaults
- requests/summary export 支持 `json` / `csv` / `markdown`
- ops-report 支持直接 JSON 读侧和同格式导出
- `requests/export` 必须放在 `/{request_id}` 前面，避免被动态路由吞掉

## Diagnostics
- `category_coverage`
- `entity_link_coverage`
- `assignment_coverage`
- `terminal_state_coverage`
- `bootstrap_ready`

## Non-Goals
- 不改 `eco_router.py`
- 不改 `eco_service.py`
- 不做审批写侧编排
