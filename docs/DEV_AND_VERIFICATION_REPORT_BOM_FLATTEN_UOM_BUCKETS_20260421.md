# Report BOM Flatten UOM Buckets Delivery

Date: 2026-04-21

## 1. Goal

Close the legacy report read-surface gap after BOM storage, compare, where-used exports, and rollup child rows became UOM-aware.

Before this increment, `ReportService._flatten_bom()` grouped flattened BOM quantities only by `child_id`. If the same component appeared in both `EA` and `MM`, the legacy report path summed both quantities into one row and lost the unit dimension.

After this increment:

- flattened BOM buckets use `(child_id, normalized_uom)`
- flattened BOM rows expose `uom`
- BOM comparison diffs expose `uom` and `bucket_key`
- diff rows preserve legacy `id=child_id` instead of replacing it with a composite key

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/report_service.py`
- `src/yuantus/meta_engine/tests/test_report_service_bom_uom.py`
- `docs/DEV_AND_VERIFICATION_BOM_ROLLUP_UOM_CHILD_VISIBILITY_20260421.md`
- `docs/DEV_AND_VERIFICATION_WHERE_USED_UOM_EXPORT_COLUMNS_20260421.md`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- BOM write paths
- BOMService compare semantics
- BOMRollupService math
- report router definitions
- schema / migrations
- scheduler / shared-dev 142 runtime

## 3. Implementation

### 3.1 Flatten Buckets

`ReportService._flatten_bom()` now normalizes each relationship UOM through the existing BOM helper:

```python
uom = _normalize_bom_uom(props.get("uom"))
bucket_key = f"{child_id}::{uom}"
```

Each summary bucket stores:

- `id`: original child item id
- `name`: child display name
- `qty`: accumulated numeric quantity
- `uom`: normalized unit

### 3.2 Flattened BOM Rows

`get_flattened_bom()` now returns:

```python
{"id": child_id, "name": name, "total_quantity": qty, "uom": uom}
```

This preserves legacy fields and adds `uom`. Same child with different UOMs now appears as separate rows.

### 3.3 BOM Comparison Diffs

`generate_bom_comparison()` now compares internal UOM bucket keys but keeps diff `id` as the child id.

Added diff fields:

- `bucket_key`: internal `child_id::UOM` comparison bucket
- `uom`: normalized UOM for the bucket

This avoids breaking consumers that interpret `id` as an item id while still making the UOM bucket explicit.

## 4. Tests

Focused command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_report_service_bom_uom.py
```

Result:

```text
5 passed in 0.16s
```

Broader adjacent regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_report_service_bom_uom.py \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
42 passed, 1 warning in 1.21s
```

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/report_service.py \
  src/yuantus/meta_engine/tests/test_report_service_bom_uom.py
git diff --check
```

Result:

```text
passed
```

## 5. Added Coverage

- `test_flatten_bom_keeps_same_child_different_uom_separate`
- `test_flatten_bom_merges_same_normalized_uom_bucket`
- `test_flatten_bom_defaults_missing_uom_to_ea`
- `test_get_flattened_bom_returns_uom_without_changing_legacy_fields`
- `test_generate_bom_comparison_reports_uom_buckets_separately`

These tests pin the critical behavior:

- same child with `EA` and `MM` does not collapse
- same child with `" ea "` and `"EA"` merges into one normalized bucket
- missing UOM defaults to `EA`
- flattened report rows keep `id/name/total_quantity` and add `uom`
- compare diffs keep `id=child_id` and add `bucket_key/uom`

## 6. Compatibility

This is a semantic tightening for legacy BOM report paths.

Additive fields:

- flattened rows add `uom`
- compare diff rows add `bucket_key` and `uom`

Intentional behavior change:

- same child with different UOMs now returns multiple report buckets instead of one summed row
- compare stats may shift from one synthetic modified row to add/remove/modified rows per UOM bucket

## 7. Review Checklist

| # | Check |
|---|---|
| 1 | `_flatten_bom()` buckets by child id and normalized UOM |
| 2 | `get_flattened_bom()` keeps legacy fields and adds `uom` |
| 3 | `generate_bom_comparison()` keeps `id=child_id` |
| 4 | Compare diffs expose `bucket_key` and `uom` |
| 5 | Missing UOM defaults to `EA` |
| 6 | No schema / scheduler / 142 runtime changes |

## 8. Follow-Up

The remaining known UOM read/reporting gap is `BaselineService.compare_baselines()`: baseline snapshots do not carry UOM buckets. That has broader snapshot compatibility implications and should remain a separate bounded increment.
