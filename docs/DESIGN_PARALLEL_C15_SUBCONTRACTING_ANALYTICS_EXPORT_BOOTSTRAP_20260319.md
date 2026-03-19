# C15 Subcontracting Analytics Export Bootstrap Design

## Goal
- 在现有 `subcontracting` bootstrap 上补齐 analytics 和 export 读侧。

## Scope
- `GET /api/v1/subcontracting/overview`
- `GET /api/v1/subcontracting/vendors/analytics`
- `GET /api/v1/subcontracting/receipts/analytics`
- `GET /api/v1/subcontracting/export/overview`
- `GET /api/v1/subcontracting/export/vendors`
- `GET /api/v1/subcontracting/export/receipts`

## Defaults
- export 支持 `json` / `csv`
- 继续复用现有 `subcontracting_router` 主应用注册
- 只做轻量读模型，不碰制造核心服务

## Analytics
- queue / order overview
- vendor analytics
- receipt analytics

## Non-Goals
- 不改 `manufacturing` 核心服务
- 不做采购或收货单据联动
- 不做持久化账本增强
