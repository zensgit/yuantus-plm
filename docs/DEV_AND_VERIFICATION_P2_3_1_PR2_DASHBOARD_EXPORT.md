# P2-3.1 PR-2: Dashboard Export — Development & Verification

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-16
**Status:** ✅ 241 passed, 0 failed (11 focused export tests)

---

## Scope

在已有 items query 基础上增加导出入口。CSV + JSON。列和 dashboard items 完全一致，不搞第二套口径。

---

## Endpoint

```
GET /api/v1/eco/approvals/dashboard/export?fmt=json|csv
    &status=overdue|pending|escalated
    &stage_id=...
    &assignee_id=...
    &role=...
    &company_id=...
    &eco_type=...
    &eco_state=...
    &deadline_from=...
    &deadline_to=...
    &limit=1000
```

| fmt | Content-Type | Content-Disposition |
|---|---|---|
| `json` | `application/json` | `attachment; filename="approval_dashboard.json"` |
| `csv` | `text/csv` | `attachment; filename="approval_dashboard.csv"` |

Bad format (e.g. `xml`) → 400。

Default limit = 1000（items 默认 50，export 放宽）。

---

## Implementation

```python
# eco_service.py
_EXPORT_COLUMNS = [
    "eco_id", "eco_name", "eco_state", "stage_id", "stage_name",
    "approval_id", "assignee_id", "assignee_username",
    "approval_type", "required_role", "is_overdue", "is_escalated",
    "approval_deadline", "hours_overdue",
]

def export_dashboard_items(self, fmt="json", **filter_kwargs) -> str:
    items = self.get_approval_dashboard_items(**filter_kwargs)
    if fmt == "csv":
        # csv.DictWriter with _EXPORT_COLUMNS
    else:
        # json.dumps
```

**关键约束**: `export_dashboard_items` 调用 `get_approval_dashboard_items` — 同一 query、同一 base、同一 filters。不存在口径分叉。

---

## Files Changed

| File | Change |
|---|---|
| `services/eco_service.py` | `_EXPORT_COLUMNS` + `export_dashboard_items(fmt, **kwargs)` |
| `web/eco_router.py` | `GET /approvals/dashboard/export` + `Response` import |
| `tests/test_eco_approval_dashboard_export.py` | **新建** — 11 focused tests |

---

## Focused Tests (11)

```
TestExportService (6)
  test_json_output_is_valid_json                        PASSED
  test_csv_output_has_header_and_rows                   PASSED
  test_csv_columns_match_export_columns                 PASSED
  test_export_passes_filters_to_items                   PASSED
  test_empty_items_produces_csv_header_only             PASSED
  test_empty_items_produces_json_empty_array            PASSED

TestExportHTTP (5)
  test_route_registered                                 PASSED
  test_json_export_200                                  PASSED
  test_csv_export_200                                   PASSED
  test_bad_format_400                                   PASSED
  test_filters_forwarded                                PASSED
```

---

## Verification

```bash
# PR-2 focused
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py -v
# Expected: 11 passed

# Dashboard suite (PR-1 + PR-1a + PR-2)
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  -v
# Expected: 39 passed

# Full regression
python3 -m pytest src/yuantus/meta_engine/tests/ -q
# Expected: 241 passed
```

---

## Next: PR-3 (Approval Ops Audit)

轻量异常读面：auto-assign 失败、no candidate、escalated approvals。
