# Parallel Doc-Sync Gate Warn/Block Mode

## Date

2026-04-04

## Purpose

Implement the second checkout-gate package from the doc-sync governance audit:

- keep existing threshold semantics
- add explicit `block|warn` gate mode
- preserve `409` blocking behavior for `block`
- allow checkout to proceed for `warn` while still surfacing threshold hits

This package does not implement asymmetric thresholds and does not change
doc-sync analytics or export surfaces.

## Scope

- `DocumentMultiSiteService.evaluate_checkout_sync_gate`
- `POST /items/{item_id}/checkout`
- focused service/router tests

## Changes

### 1. Gate mode normalization

`evaluate_checkout_sync_gate(..., mode="block")` now accepts:

- `block`
- `warn`

Invalid values raise `ValueError("mode must be block or warn")`.

### 2. Service verdict contract

The gate payload now includes:

- `mode`
- `verdict`: `clear | warn | block`
- `threshold_exceeded`
- `warning`

Behavior:

- threshold hit + `mode=block` -> `verdict=block`, `blocking=true`
- threshold hit + `mode=warn` -> `verdict=warn`, `warning=true`, `blocking=false`
- no threshold hit -> `verdict=clear`

Existing `blocking_reasons`, `blocking_counts`, and `blocking_jobs` are retained.

### 3. Checkout router behavior

`POST /items/{item_id}/checkout` now accepts:

- `doc_sync_gate_mode` with default `block`

Behavior:

- `block`: unchanged `409 doc_sync_checkout_blocked`
- `warn`: checkout continues, response stays `200`, warning is exposed via headers:
  - `X-Doc-Sync-Gate-Verdict`
  - `X-Doc-Sync-Gate-Threshold-Hits`

No success payload body shape changes were introduced.

## Why This Scope

The audit split the remaining work into:

1. direction-aware filtering
2. warn/block mode

This package only closes the second item. Per-direction asymmetric thresholds are
still a follow-on enhancement, not part of this patch.

## Result

- checkout gate now supports operator-friendly warn-only mode
- existing block mode remains backward compatible
- no schema migration
- no discoverability/export changes
