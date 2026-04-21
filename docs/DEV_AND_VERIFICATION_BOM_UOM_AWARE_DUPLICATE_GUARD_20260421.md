# BOM UOM-Aware Duplicate Guard Delivery

Date: 2026-04-21

## 1. Goal

Close the remaining medium-scope follow-up from the CAD BOM import dedup line: allow the same `(parent, child)` pair to exist as distinct BOM relationship lines when `uom` differs.

Before this increment, `BOMService.get_bom_line_by_parent_child(parent, child)` ignored `uom`, so a second line for the same child with a different `uom` was rejected as duplicate.

After this increment:

- same `(parent, child, normalized_uom)` still rejects as duplicate
- same `(parent, child)` with different normalized `uom` is allowed
- delete-by-parent-child remains compatible for single-line cases
- delete-by-parent-child becomes explicit for multi-line cases: callers must pass `uom`

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py`
- `docs/DEV_AND_VERIFICATION_BOM_IMPORT_DEDUP_AGGREGATION_20260421.md`
- `docs/DEV_AND_VERIFICATION_REFDES_NATURAL_SORT_20260421.md`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- schema / migrations
- BOM compare line-key semantics
- where-used APIs
- scheduler / CAD backend profile / shared-dev 142 assets
- UI

## 3. Implementation

### 3.1 Service

`BOMService` now has:

- `_normalize_bom_uom(value, default="EA")`
- `get_bom_lines_by_parent_child(parent_item_id, child_item_id)`
- `get_bom_line_by_parent_child(parent_item_id, child_item_id, *, uom=None)`

Compatibility behavior:

- `uom=None` preserves legacy first-match behavior for existing callers.
- `uom="..."` performs normalized UOM-aware matching.

`add_child()` now checks duplicates with `uom=normalized_uom` and stores normalized UOM in the relationship properties.

### 3.2 Remove Behavior

`remove_child(parent_id, child_id, uom=None)` now behaves as follows:

- one matching line and no `uom`: remove it, preserving legacy behavior
- multiple matching lines and no `uom`: raise `ValueError("Multiple BOM relationships found ... specify uom")`
- `uom` supplied: remove the matching UOM-specific line

The router delete endpoint now accepts optional `?uom=...`. Ambiguous multi-line deletes return HTTP 400; not-found still returns HTTP 404.

## 4. Tests

Focused service/import command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py
```

Result:

```text
30 passed, 1 warning in 1.28s
```

Adjacent regression + doc-index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_suspended_write_paths.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
64 passed, 1 warning in 1.39s
```

Static and diff hygiene:

```bash
git diff --check
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/bom_service.py \
  src/yuantus/meta_engine/services/cad_bom_import_service.py \
  src/yuantus/meta_engine/web/bom_router.py
```

Result: passed.

## 5. Added / Updated Coverage

New real-session tests:

- `test_add_child_allows_same_parent_child_when_uom_differs`
- `test_add_child_rejects_same_normalized_uom_duplicate`
- `test_get_bom_line_by_parent_child_disambiguates_by_uom`
- `test_remove_child_requires_uom_when_multiple_lines_exist`
- `test_remove_child_with_uom_removes_selected_line`

Updated CAD BOM import real-session test:

- `test_import_bom_real_session_different_uom_creates_two_bom_lines`

The updated CAD import test now asserts:

- `dedup_aggregated == 0`
- `created_lines == 2`
- `skipped_lines == 0`
- persisted Part BOM line UOMs are `["EA", "MM"]`

## 6. Compatibility

Existing callers that only have one current parent/child line continue to work unchanged.

The only intentional behavior change is for ambiguous deletes after multiple UOM-specific lines exist. A delete request without `uom` now fails fast instead of deleting an arbitrary first match.

## 7. Review Checklist

| # | Check |
|---|---|
| 1 | Same normalized UOM duplicate is still blocked |
| 2 | Different normalized UOM lines can coexist |
| 3 | Stored UOM is normalized to uppercase |
| 4 | Legacy first-match lookup behavior is preserved when `uom=None` |
| 5 | Multi-line remove without `uom` returns an explicit ambiguity error |
| 6 | Router maps ambiguity to HTTP 400 and not-found to HTTP 404 |
| 7 | CAD BOM import real-session test now creates two lines instead of skipping one |
| 8 | No schema / migration / scheduler / UI files touched |

## 8. Follow-Up

The comparison-side follow-up for UOM-aware summarized / by-item line keys is closed by `DEV_AND_VERIFICATION_BOM_COMPARE_UOM_AWARE_LINE_KEYS_20260421.md`.

The where-used impact / cockpit export read-surface follow-up is closed by `DEV_AND_VERIFICATION_WHERE_USED_UOM_EXPORT_COLUMNS_20260421.md`.

If product wants richer UOM governance later, that should be a separate tenant-level UOM dictionary/configuration feature, not hardcoded synonyms in BOMService.
