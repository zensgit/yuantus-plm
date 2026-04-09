# Parallel Doc-Sync Gate Directional Thresholds

## Date

2026-04-04

## Purpose

Close the remaining asymmetric-threshold gap from the doc-sync checkout
governance audit.

This package adds per-direction threshold overrides for checkout gate
evaluation without changing analytics/export surfaces.

## Scope

- `DocumentMultiSiteService.evaluate_checkout_sync_gate`
- `POST /items/{item_id}/checkout`
- focused service/router tests

## Changes

### 1. Direction threshold input

The gate now accepts:

- `direction_thresholds: {"push": {...}, "pull": {...}}`

Supported per-direction status keys:

- `pending`
- `processing`
- `failed`
- `dead_letter`

All values must be non-negative integers.

### 2. Effective threshold selection

The gate continues to compute a single effective direction:

- explicit request direction first
- otherwise site default direction
- otherwise all-directions fallback

When `effective_direction` is `push` or `pull`, matching overrides from
`direction_thresholds` are merged onto the base thresholds.

### 3. Response contract

The gate response now includes:

- `direction_thresholds`
- `thresholds`

`thresholds` remains the effective threshold set actually used for decision
making, so existing callers do not need to recalculate the applied values.

### 4. Checkout router pass-through

`POST /items/{item_id}/checkout` now accepts:

- `doc_sync_direction_thresholds`

The router passes the object through unchanged to gate evaluation and preserves
existing block/warn behavior.

## Result

The original B2+B1 audit split is now fully implemented:

1. direction-aware filtering
2. warn/block mode
3. asymmetric direction thresholds

No migration, no export changes, no analytics redesign.
