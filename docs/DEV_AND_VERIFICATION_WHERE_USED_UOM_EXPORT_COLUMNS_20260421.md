# Where-Used UOM Export Columns Delivery

Date: 2026-04-21

## 1. Goal

Close the read-surface gap left after BOM storage and compare became UOM-aware.

Before this increment, where-used consumers could still distinguish UOM-specific BOM rows only by parsing the nested `line` object. Impact summary exports, item cockpit exports, and product detail samples did not expose first-class `quantity` / `uom` fields.

After this increment:

- impact where-used hits expose `quantity` and normalized `uom`
- impact summary ZIP `where_used.csv` includes `quantity,uom`
- item cockpit ZIP `where_used.csv` includes `quantity,uom`
- product detail where-used sample includes `relationship_id`, `quantity`, normalized `uom`, and original `line`

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/impact_analysis_service.py`
- `src/yuantus/meta_engine/services/product_service.py`
- `src/yuantus/meta_engine/web/impact_router.py`
- `src/yuantus/meta_engine/web/item_cockpit_router.py`
- `src/yuantus/meta_engine/tests/test_impact_router.py`
- `src/yuantus/meta_engine/tests/test_impact_export_bundles.py`
- `src/yuantus/meta_engine/tests/test_item_cockpit_router.py`
- `src/yuantus/meta_engine/tests/test_product_detail_cockpit_extensions.py`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- BOM storage semantics
- BOM compare line keys
- BOM rollup / report / baseline legacy surfaces
- schema / migrations
- scheduler / shared-dev 142 runtime

## 3. Implementation

### 3.1 Impact Summary

`ImpactAnalysisService.where_used_summary()` now promotes:

- `quantity` from `entry["line"]["quantity"]`
- `uom` from `entry["line_normalized"]["uom"]`, falling back to `entry["line"]["uom"]`

The nested `line` object remains unchanged for backward compatibility.

### 3.2 Impact and Cockpit CSV Exports

The where-used CSV columns now use:

```text
parent_id,parent_number,parent_name,relationship_id,level,quantity,uom,line
```

This keeps the existing nested `line` payload while making UOM-specific rows directly sortable/filterable in exported CSV.

### 3.3 Product Detail Sample

`ProductDetailService._get_where_used_summary()` now includes:

- `relationship_id`
- `quantity`
- normalized `uom`
- original `line`

This prevents the product detail sample from showing two same-parent rows as indistinguishable duplicates when they differ only by UOM.

## 4. Tests

Focused command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_impact_router.py \
  src/yuantus/meta_engine/tests/test_impact_export_bundles.py \
  src/yuantus/meta_engine/tests/test_item_cockpit_router.py \
  src/yuantus/meta_engine/tests/test_product_detail_cockpit_extensions.py
```

Result:

```text
15 passed in 4.67s
```

Broader adjacent regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_impact_router.py \
  src/yuantus/meta_engine/tests/test_impact_export_bundles.py \
  src/yuantus/meta_engine/tests/test_item_cockpit_router.py \
  src/yuantus/meta_engine/tests/test_product_detail_cockpit_extensions.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
47 passed, 1 warning in 5.39s
```

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/impact_analysis_service.py \
  src/yuantus/meta_engine/services/product_service.py \
  src/yuantus/meta_engine/web/impact_router.py \
  src/yuantus/meta_engine/web/item_cockpit_router.py
git diff --check
```

Result:

```text
passed
```

## 5. Added Coverage

- `test_where_used_summary_promotes_quantity_and_normalized_uom`
- `test_impact_summary_returns_domain_summaries`
- `test_impact_summary_export_zip_happy_path`
- `test_cockpit_happy_path_includes_impact_readiness_ecos_and_links`
- `test_cockpit_export_zip_contains_expected_files`
- `test_where_used_summary_sample_exposes_relationship_quantity_and_uom`

These tests pin the important behavior:

- normalized UOM is promoted when `line_normalized` is present
- original nested `line` is preserved
- CSV exports expose `quantity,uom` as first-class columns
- product detail samples expose `relationship_id` and UOM enough to distinguish same-parent rows

## 6. Compatibility

This is an additive read-surface change.

Existing JSON clients that read the nested `line` object continue to work. CSV consumers see two new columns inserted before `line`; this is intentional because `line` remains the raw nested payload while `quantity/uom` are now the operator-facing columns.

## 7. Review Checklist

| # | Check |
|---|---|
| 1 | Where-used service promotes normalized UOM, not raw lower-case UOM |
| 2 | Raw nested `line` is preserved unchanged |
| 3 | Impact response model includes `quantity` and `uom` |
| 4 | Impact ZIP `where_used.csv` includes `quantity,uom` |
| 5 | Cockpit ZIP `where_used.csv` includes `quantity,uom` |
| 6 | Product detail sample includes `relationship_id` and UOM |
| 7 | No schema / scheduler / 142 runtime changes |

## 8. Follow-Up

Not closed by this increment:

- `BOMRollupService` child rows do not expose `uom`
- legacy `ReportService._flatten_bom()` still buckets by child without UOM
- `BaselineService.compare_baselines()` snapshots do not carry UOM buckets

Those are separate read/reporting increments because each has different downstream compatibility risk.
