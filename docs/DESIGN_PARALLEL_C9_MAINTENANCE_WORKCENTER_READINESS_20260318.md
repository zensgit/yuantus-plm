# C9 – Maintenance-Workcenter Readiness

**Branch**: `feature/claude-c9-maintenance-readiness`
**Date**: 2026-03-18
**Status**: Implemented & Verified

---

## 1. Objective

Extend the C5 maintenance domain with workcenter-level readiness
and scheduling capabilities:
- Equipment readiness summary with status aggregation
- Preventive maintenance window and overdue detection
- Exportable maintenance work queue with priority ranking

## 2. New Service Methods

### MaintenanceService

| Method | Purpose |
|---|---|
| `get_equipment_readiness_summary()` | Aggregate equipment health by plant/workcenter |
| `get_preventive_schedule()` | Identify overdue and upcoming preventive maintenance |
| `get_maintenance_queue_summary()` | Build prioritized active work queue |

### get_equipment_readiness_summary

Parameters: `plant_code`, `workcenter_id` (both optional filters)

Returns:
```json
{
  "total_equipment": 10,
  "operational": 8,
  "readiness_pct": 80.0,
  "status_counts": {"operational": 8, "in_maintenance": 1, "out_of_service": 1},
  "needs_attention": [
    {"equipment_id": "eq-3", "name": "Lathe #2", "status": "in_maintenance", ...}
  ],
  "filters": {"plant_code": "PLT-A", "workcenter_id": null}
}
```

### get_preventive_schedule

Parameters: `reference_date` (defaults to now), `window_days` (default 30),
`include_overdue` (default true)

Returns:
```json
{
  "reference_date": "2026-03-18T00:00:00",
  "window_days": 30,
  "overdue": [{"request_id": "mr-1", "days_overdue": 30, ...}],
  "overdue_count": 1,
  "upcoming": [{"request_id": "mr-2", "days_until_due": 7, ...}],
  "upcoming_count": 1
}
```

Only active (draft/submitted/in_progress) preventive requests with
a due_date are considered. Done and cancelled requests are excluded.

### get_maintenance_queue_summary

Parameters: `plant_code`, `workcenter_id` (both optional)

Returns:
```json
{
  "total_active": 5,
  "by_priority": {"urgent": 1, "high": 2, "medium": 2},
  "by_type": {"corrective": 3, "preventive": 2},
  "by_state": {"draft": 1, "submitted": 3, "in_progress": 1},
  "queue": [...],
  "filters": {"plant_code": null, "workcenter_id": "wc-1"}
}
```

Queue items are sorted by priority (urgent first) then state.

## 3. New Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/maintenance/equipment/readiness-summary` | Equipment health snapshot |
| GET | `/maintenance/preventive-schedule` | Overdue + upcoming PM window |
| GET | `/maintenance/queue-summary` | Exportable active work queue |

### Route Ordering

`/equipment/readiness-summary` is registered **before**
`/equipment/{equipment_id}` to prevent FastAPI from matching
"readiness-summary" as an equipment ID path parameter.

## 4. Design Decisions

1. **Read-only aggregation**: All three endpoints are pure read
   operations that aggregate existing data without modifying state.

2. **In-memory filtering for workcenter**: Since workcenter_id is on
   equipment (not requests), queue and readiness filter by joining
   through equipment lookup. This avoids adding workcenter columns
   to the request model.

3. **No new tables or columns**: All C9 features are built entirely
   on existing C5 model columns. No schema changes required.

4. **Graceful empty handling**: All summaries return valid zero-state
   responses when no data matches the filters.
