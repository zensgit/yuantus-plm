# C13 Subcontracting Bootstrap Design

## Goal
Add an isolated subcontracting bootstrap module that exposes a minimal read model and vendor/material issue/receipt skeleton without modifying the manufacturing routing service.

## Scope
- new `subcontracting` models and service
- new `subcontracting_router`
- app registration
- service/router tests

## Reused Signals
- `Operation.is_subcontracted`
- `Operation.subcontractor_id`
- `Operation.routing_id`

## Delivered Contract
- `POST /api/v1/subcontracting/orders`
- `GET /api/v1/subcontracting/orders`
- `GET /api/v1/subcontracting/orders/{order_id}`
- `POST /api/v1/subcontracting/orders/{order_id}/assign-vendor`
- `POST /api/v1/subcontracting/orders/{order_id}/issue-material`
- `POST /api/v1/subcontracting/orders/{order_id}/record-receipt`
- `GET /api/v1/subcontracting/orders/{order_id}/timeline`

## Non-Goals
- no routing/MRP orchestration rewrite
- no manufacturing router changes beyond standalone router registration
- no purchase workflow integration yet
