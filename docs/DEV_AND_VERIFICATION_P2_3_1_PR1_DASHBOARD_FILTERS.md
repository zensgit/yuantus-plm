# P2-3.1 PR-1: Dashboard Filters — Development & Verification

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-16
**Status:** ✅ 241 passed, 0 failed (26 dashboard tests, +9 new filter tests)

---

## Scope

扩展 dashboard 读面过滤能力。只扩读面，不动审批写路径。

---

## New Filter Parameters

| Parameter | Type | Description | Applied to |
|---|---|---|---|
| `company_id` | `str` | Filter by ECO.company_id | summary + items |
| `eco_type` | `str` | Filter by ECO.eco_type (bom/routing/...) — serves as category | summary + items |
| `eco_state` | `str` | Override default draft+progress filter (e.g. only "progress") | summary + items |
| `deadline_from` | `ISO datetime` | approval_deadline >= value | summary + items |
| `deadline_to` | `ISO datetime` | approval_deadline <= value | summary + items |

All filters are optional. When omitted, behavior is unchanged (backward compatible).

---

## Implementation

Filters are injected at `_base_dashboard_query()` level → summary and items see identical scope:

```python
def _base_dashboard_query(self, *, company_id=None, eco_type=None,
                          eco_state=None, deadline_from=None, deadline_to=None):
    states = [eco_state] if eco_state else [DRAFT, PROGRESS]
    query = session.query(ECO, ECOStage, ECOApproval).join(...).filter(
        ECO.state.in_(states), ...
    )
    if company_id:  query = query.filter(ECO.company_id == company_id)
    if eco_type:    query = query.filter(ECO.eco_type == eco_type)
    if deadline_from: query = query.filter(ECO.approval_deadline >= deadline_from)
    if deadline_to:   query = query.filter(ECO.approval_deadline <= deadline_to)
    return query
```

Both `get_approval_dashboard_summary()` and `get_approval_dashboard_items()` accept the same kwargs and forward to `_base_dashboard_query()`.

Router parses ISO datetime strings at the boundary.

---

## Files Changed

| File | Change |
|---|---|
| `services/eco_service.py` | `_base_dashboard_query` +5 kwargs; `get_approval_dashboard_summary` +5 kwargs; `get_approval_dashboard_items` +5 kwargs |
| `web/eco_router.py` | Both GET endpoints +5 Query params; ISO datetime parsing |
| `tests/test_eco_approval_dashboard.py` | +9 filter tests |

---

## Filter Tests (9 new)

```
TestDashboardFilters (9)
  test_base_query_accepts_company_id                    PASSED
  test_base_query_accepts_eco_type                      PASSED
  test_base_query_accepts_eco_state                     PASSED
  test_base_query_accepts_deadline_range                PASSED
  test_summary_passes_filters_to_base_query             PASSED
  test_items_passes_filters_to_base_query               PASSED
  test_router_summary_accepts_filter_params             PASSED
  test_router_items_accepts_filter_params               PASSED
  test_summary_filters_consistent_with_items            PASSED
```

---

## Verification

```bash
# PR-1 focused
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py -v
# Expected: 26 passed

# Full regression
python3 -m pytest src/yuantus/meta_engine/tests/ -q
# Expected: 241 passed
```

---

---

## PR-1a Fix: Deadline Input Validation

**问题**: `deadline_from` / `deadline_to` 是 `str` 类型，坏输入 `fromisoformat` 抛 ValueError → 500。

**修复**: 抽取 `_parse_deadline(value, param_name)` 共享 helper，catch ValueError → 400 with clear message。

```python
def _parse_deadline(value, param_name):
    if not value: return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(400, f"Invalid {param_name}: '{value}' is not a valid ISO datetime")
```

Both `summary` and `items` endpoints use `_parse_deadline`.

**Tests:**
- `test_invalid_deadline_from_returns_400` — bad string → 400 + detail contains "deadline_from"
- `test_invalid_deadline_to_returns_400` — bad string → 400 + detail contains "deadline_to"

**Total dashboard tests: 28** (17 P2-3 + 9 PR-1 filters + 2 PR-1a validation)

---

## Next: PR-2 (Dashboard Export)

- CSV + JSON export from the same filtered items query
- Same filter params as items endpoint
- No new statistics 口径
