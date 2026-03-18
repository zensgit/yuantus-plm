# C4 – Quality Domain Bootstrap

**Date**: 2026-03-18
**Branch**: `feature/claude-c4-quality`
**Status**: Implemented

## 1. Objective

Create an isolated quality assurance module that mirrors Odoo 18
`quality_control` / `quality_mrp` concepts without touching existing
hot-path PLM files.

### Odoo 18 Concepts Mapped

| Odoo Model | Yuantus Model | Purpose |
|---|---|---|
| `quality.point` | `QualityPoint` | Template defining when/what to check |
| `quality.check` | `QualityCheck` | Individual inspection instance |
| `quality.alert` | `QualityAlert` | Non-conformance / issue tracker |

## 2. Architecture

```
quality/
├── __init__.py          # Package marker
├── models.py            # QualityPoint, QualityCheck, QualityAlert + enums
└── service.py           # QualityService – CRUD + domain logic

web/
└── quality_router.py    # REST API: /quality/points, /checks, /alerts

tests/
└── test_quality_service.py  # 18 tests
```

### 2.1 Enums

| Enum | Values |
|---|---|
| `QualityCheckType` | pass_fail, measure, take_picture, worksheet, instructions |
| `QualityCheckResult` | none, pass, fail, warning |
| `QualityAlertState` | new, confirmed, in_progress, resolved, closed |
| `QualityAlertPriority` | low, medium, high, critical |

### 2.2 State Machine – Quality Alert

```
new → confirmed → in_progress → resolved → closed
 │         │            │            │
 └─closed  └─closed     └─closed     └─in_progress (reopen)
```

### 2.3 Auto-Evaluation – Measure Checks

When a `measure` check records a value, the system auto-evaluates
against `measure_min` / `measure_max` from the parent QualityPoint:
- In range → `pass`
- Out of range → `fail`

## 3. API Surface

### Quality Points
| Method | Path | Description |
|---|---|---|
| POST | `/quality/points` | Create quality control point |
| GET | `/quality/points` | List points (filter by product, type, active) |
| GET | `/quality/points/{id}` | Get point detail |
| PATCH | `/quality/points/{id}` | Update point fields |

### Quality Checks
| Method | Path | Description |
|---|---|---|
| POST | `/quality/checks` | Create check from a point |
| POST | `/quality/checks/{id}/record` | Record check result |
| GET | `/quality/checks` | List checks (filter by point, product, result) |
| GET | `/quality/checks/{id}` | Get check detail |

### Quality Alerts
| Method | Path | Description |
|---|---|---|
| POST | `/quality/alerts` | Create alert |
| POST | `/quality/alerts/{id}/transition` | Advance alert state |
| GET | `/quality/alerts` | List alerts (filter by state, priority, product) |
| GET | `/quality/alerts/{id}` | Get alert detail |

## 4. Design Decisions

1. **Isolated module** – Zero imports from existing PLM hot-path files.
2. **JSONB properties** – Extensible metadata on all three models.
3. **Trigger field** – `trigger_on` supports manual/receipt/production/transfer
   for future MRP integration.
4. **State machine** – Explicit allowed transitions; closed is terminal.
5. **Measure auto-eval** – Removes human error for threshold-based checks.
