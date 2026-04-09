# C12 - Approvals Domain Surpass Design (2026-03-23)

## 1. Goal

Extend the generic approvals bootstrap with a consumer-grade read layer and queue observability without changing the database schema.

The baseline already provides:
- category CRUD
- approval request CRUD
- state transitions
- summary / ops report exports

This surpass increment adds:
- request age visibility in read models
- bounded request history and audit proof
- tolerant request batch pack-summary for downstream consumers
- queue health analysis with stale backlog detection
- exportable queue health report in JSON / CSV / Markdown
- consistent generated-at timestamps across observability outputs

## 2. API Changes

### GET `/approvals/requests/{request_id}/consumer-summary`

Returns a consumer-oriented request payload with:
- `request`
- `status`
- `proof.assignment`
- `proof.lifecycle`
- `proof.audit`
- `proof.history_api`
- `proof.allowed_transitions`

Query parameters:
- `include_history`
- `history_limit`

### GET `/approvals/requests/{request_id}/history`

Returns a bounded synthetic history derived from the current request lifecycle:
- `request_id`
- `current_state`
- `total`
- `latest`
- `events`
- `generated_at`

### POST `/approvals/requests/pack-summary`

Returns a tolerant batch summary for `request_ids` with:
- `requested_count`
- `found_count`
- `not_found_count`
- `pending_count`
- `terminal_count`
- `unassigned_pending_count`
- `generated_at`
- `requests`

Missing request IDs do not fail the whole batch.

### GET `/approvals/queue-health`

Returns a queue health snapshot with:
- `generated_at`
- `filters`
- `thresholds` (`warn_after_hours`, `stale_after_hours`)
- `total`, `pending`, `pending_ratio`
- `by_state`, `by_priority`
- `pending_age`
  - `oldest_hours`
  - `average_hours`
  - `oldest_request`
  - `fresh_count`
  - `watch_count`
  - `stale_count`
- `unassigned_pending_count`
- `risk_flags`
- `health_status`
- `operational_ready`

### GET `/approvals/queue-health/export`

Returns the same queue health information as:
- JSON payload
- CSV metrics export
- Markdown report

### Request read-model enhancement

The existing approvals request read model now includes:
- `age_hours`

This is available in:
- request detail
- request list
- request export

## 3. Health Rules

- `warn_after_hours` defaults to `4`
- `stale_after_hours` defaults to `24`
- pending requests older than `stale_after_hours` are counted as stale
- pending requests without an assignee are counted separately
- `risk_flags` currently include:
  - `stale_pending_backlog`
  - `unassigned_pending_work`
  - `pending_pressure`

## 4. Implementation Notes

- No migrations are required.
- Aging is derived from `created_at` only.
- Request history is derived from the persisted lifecycle columns already present on the request row.
- The history view is intentionally bounded by `history_limit` and is meant for consumer proof, not durable event sourcing.
- Batch pack-summary reuses the same consumer-summary contract and tolerates missing request IDs.
- Timezone-aware timestamps are normalized to UTC-naive values before age calculations.
- Markdown / CSV exports reuse the same helper patterns as existing approvals exports.

## 5. Files

- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/meta_engine/web/approvals_router.py`
- `src/yuantus/meta_engine/tests/test_approvals_service.py`
- `src/yuantus/meta_engine/tests/test_approvals_router.py`
