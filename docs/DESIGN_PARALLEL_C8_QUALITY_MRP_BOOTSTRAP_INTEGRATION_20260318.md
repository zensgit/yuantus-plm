# C8 – Quality-MRP Bootstrap Integration

**Branch**: `feature/claude-c8-quality-mrp`
**Date**: 2026-03-18
**Status**: Implemented, Codex-integrated & Verified

---

## 1. Objective

Extend the C4 quality domain with manufacturing-aware scoping:
- Add `routing_id` to QualityPoint and QualityCheck for MRP traceability
- Enable filtering quality points and checks by `routing_id` / `operation_id`
- Provide a manufacturing context summary endpoint for quality alerts

## 2. Model Changes

### QualityPoint
| Column | Type | New? |
|---|---|---|
| `routing_id` | String, indexed | Yes |

### QualityCheck
| Column | Type | New? |
|---|---|---|
| `routing_id` | String, indexed | Yes |
| `operation_id` | String, indexed | Yes |

Both `routing_id` and `operation_id` are copied from the parent
QualityPoint when creating a QualityCheck.

## 3. Service Changes

### QualityService

| Method | Change |
|---|---|
| `create_point()` | +`routing_id` parameter |
| `list_points()` | +`routing_id`, `operation_id` filters |
| `create_check()` | Copies `routing_id`/`operation_id` from point |
| `list_checks()` | +`routing_id`, `operation_id` filters |
| `get_alert_manufacturing_context()` | **New** – traverses alert→check→point chain |

## 4. New Endpoint

### GET /quality/alerts/{alert_id}/manufacturing-context

Returns a manufacturing context summary by traversing the
alert → check → point chain.

Response:
```json
{
  "alert_id": "qa-1",
  "alert_name": "Torque out of range",
  "alert_state": "new",
  "alert_priority": "high",
  "product_id": "item-1",
  "check": {
    "check_id": "qc-1",
    "check_type": "measure",
    "result": "fail",
    "measure_value": 25.0,
    "source_document_ref": "MO-200",
    "lot_serial": "LOT-A"
  },
  "point": {
    "point_id": "qp-1",
    "point_name": "Torque Check",
    "routing_id": "routing-1",
    "operation_id": "op-30",
    "trigger_on": "production",
    "measure_min": 10.0,
    "measure_max": 20.0,
    "measure_unit": "Nm"
  },
  "manufacturing_summary": {
    "routing_id": "routing-1",
    "operation_id": "op-30",
    "source_document_ref": "MO-200",
    "product_id": "item-1",
    "lot_serial": "LOT-A"
  }
}
```

Returns 404 if the alert does not exist. When the alert has no
associated check, `check`, `point`, and `manufacturing_summary`
fields contain null values.

## 5. Updated Endpoints

| Method | Path | Change |
|---|---|---|
| POST | `/quality/points` | +`routing_id` field |
| GET | `/quality/points` | +`routing_id`, `operation_id` query params |
| PATCH | `/quality/points/{id}` | +`routing_id`, `operation_id` updatable |
| GET | `/quality/checks` | +`routing_id`, `operation_id` query params |

Serializers (`_point_dict`, `_check_dict`) now include `routing_id`
and `operation_id` in their output.

## 6. Design Decisions

1. **Check inherits routing/operation from point**: When `create_check()`
   runs, it copies `routing_id` and `operation_id` from the parent
   point. This denormalizes the data for query performance.

2. **Manufacturing context is read-only aggregation**: The endpoint
   traverses the object graph without modifying any state. It's a
   convenience aggregation for callers that need the full picture.

3. **Graceful degradation**: Alerts without a linked check still return
   a valid response with null sub-objects, avoiding 404 for partial data.

4. **No new tables**: All changes are column additions to existing
   C4 tables and new service methods.

## 7. Codex Integration Notes (2026-03-19)

Codex-side integration verification applied three targeted adjustments:

1. **Imported C4 bootstrap into the integration branch**
   - Cherry-picked `feature/claude-c4-quality`
   - Rationale: C8 is an extension of the quality domain, not a
     standalone module.

2. **Registered `quality_router` in the main application**
   - Added `quality_router` import to `src/yuantus/api/app.py`
   - Added `app.include_router(quality_router, prefix="/api/v1")`
   - Rationale: branch-local router tests were already green, but the
     feature was not reachable from `create_app()` until this step.

3. **Removed Pydantic v2 deprecated request serialization**
   - Replaced `req.dict(exclude_unset=True)` with
     `req.model_dump(exclude_unset=True)` in `quality_router.py`
   - Rationale: keep the quality router free of new deprecation noise
     before broader integration.

## 8. Final Scope On This Integration Branch

- Quality points CRUD
- Quality checks CRUD + result recording
- Quality alerts CRUD + transitions
- Routing/operation scoped quality points and checks
- Alert manufacturing context
- Main app router registration
