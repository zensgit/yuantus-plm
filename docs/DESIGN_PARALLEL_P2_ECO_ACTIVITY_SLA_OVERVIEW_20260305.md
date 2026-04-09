# DESIGN_PARALLEL_P2_ECO_ACTIVITY_SLA_OVERVIEW_20260305

- Date: 2026-03-05
- Scope: ECO activity SLA overview (overdue / due-soon / on-track / no-due-date / closed).
- Related code:
  - `src/yuantus/meta_engine/services/parallel_tasks_service.py`
  - `src/yuantus/meta_engine/web/parallel_tasks_router.py`

## 1. Goals

1. Provide a single API view for ECO activity deadline risk triage.
2. Reuse existing `ECOActivityGate.properties` without schema migration.
3. Support operational filters (assignee, include_closed, window hours, limit).
4. Keep API contract deterministic and easy to consume by dashboard / runbook scripts.

## 2. Data Contract

1. Due date source:
- `ECOActivityGate.properties["due_at"]`.
- Accepts ISO-8601 string or datetime object.
- Timezone-aware values are normalized to UTC-naive.
- Invalid values are ignored (treated as no due date).

2. SLA classification rules:
- `closed`: terminal statuses (`completed`, `canceled`, `exception`) when `include_closed=true`.
- `overdue`: open activity with `due_at < evaluated_at`.
- `due_soon`: open activity with `evaluated_at <= due_at <= evaluated_at + due_soon_hours`.
- `on_track`: open activity with `due_at > due_soon_deadline`.
- `no_due_date`: open activity with no parseable due date.

3. Output payload keys:
- `eco_id`, `evaluated_at`, `due_soon_hours`, `due_soon_deadline`
- `include_closed`, `assignee_id`
- `total`, `open_total`, `closed_total`
- `overdue_total`, `due_soon_total`, `on_track_total`, `no_due_date_total`
- `status_counts`, `truncated`, `activities`

## 3. API Changes

1. New endpoint:
- `GET /api/v1/eco-activities/{eco_id}/sla`

2. Query params:
- `due_soon_hours` (default `24`, validated `1..720`)
- `include_closed` (default `false`)
- `assignee_id` (optional)
- `limit` (default `100`, validated `1..500`)
- `evaluated_at` (optional ISO-8601 datetime)

3. Error contract:
- Invalid SLA arguments map to `400` with code `eco_activity_sla_invalid`.
- Invalid `evaluated_at` format maps to existing `invalid_datetime` contract.

## 4. Ordering and Pagination Strategy

1. Activities are sorted for triage priority:
- `overdue` -> `due_soon` -> `on_track` -> `no_due_date` -> `closed`
- Then by due date and activity id for deterministic response.

2. `limit` applies after sorting.
- `truncated=true` signals list clipping.
- aggregate totals are always computed from the full filtered set.

## 5. Risks and Mitigations

1. Risk: due date stored in flexible JSON can be malformed.
- Mitigation: parser fail-soft behavior, classify as `no_due_date`, avoid endpoint failure.

2. Risk: client confusion around timezone.
- Mitigation: normalize aware datetimes to UTC and return normalized ISO values.

3. Risk: large ECO sets can generate oversized payloads.
- Mitigation: bounded `limit`, default 100, max 500, and `truncated` marker.

## 6. Rollback Plan

1. Revert new service helpers and `activity_sla` method.
2. Remove `/eco-activities/{eco_id}/sla` router endpoint.
3. Keep existing create/list/transition/blocker/event behavior untouched.
