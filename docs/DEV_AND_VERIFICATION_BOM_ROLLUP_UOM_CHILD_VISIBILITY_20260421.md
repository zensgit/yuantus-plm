# BOM Rollup UOM Child Visibility Delivery

Date: 2026-04-21

## 1. Goal

Close the smallest remaining UOM read-surface gap after BOM storage, compare, and where-used exports became UOM-aware.

Before this increment, BOM weight rollup computed each child relationship independently but exposed only `relationship_id`, `quantity`, and `line_weight` in `tree.children[*]`. Two rows for the same child with different UOMs were visible as separate relationships, but the rollup payload did not show the UOM dimension directly.

After this increment:

- each rollup child result includes normalized `uom`
- missing/blank UOM defaults to `EA`
- same child through two relationships with different UOM remains two child rows
- no weight conversion is performed

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/bom_rollup_service.py`
- `src/yuantus/meta_engine/tests/test_bom_rollup_service.py`
- `docs/DEV_AND_VERIFICATION_WHERE_USED_UOM_EXPORT_COLUMNS_20260421.md`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- BOM rollup math
- weight conversion / UOM conversion
- write-back behavior
- product detail rollup summary shape
- schema / migrations
- scheduler / shared-dev 142 runtime

## 3. Implementation

`BOMRollupService._compute_node()` now derives:

```python
uom = _normalize_bom_uom(rel_props.get("uom"))
```

and writes it to each child result:

```python
child_result["uom"] = uom
```

This matches existing BOM normalization semantics:

- `"ea"` -> `"EA"`
- `"mm"` -> `"MM"`
- missing/blank -> `"EA"`

The field is informational only. `line_weight` remains:

```text
child_total_weight * quantity
```

No unit conversion is attempted.

## 4. Tests

Focused command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py
```

Result:

```text
5 passed in 0.34s
```

Broader adjacent regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_product_detail_service.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_impact_router.py \
  src/yuantus/meta_engine/tests/test_impact_export_bundles.py \
  src/yuantus/meta_engine/tests/test_item_cockpit_router.py \
  src/yuantus/meta_engine/tests/test_product_detail_cockpit_extensions.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
59 passed, 1 warning in 5.82s
```

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py
git diff --check
```

Result:

```text
passed
```

## 5. Added Coverage

- `test_compute_node_handles_missing_weights`
- `test_compute_node_exposes_uom_per_relationship_without_collapsing_child_rows`
- `test_compute_node_defaults_missing_uom_to_ea`

These tests pin the critical behavior:

- child rollup rows expose normalized UOM
- same child with two different relationship UOMs remains two child rows
- missing UOM defaults to `EA`
- line weight math remains quantity-based and unchanged

## 6. Compatibility

This is an additive response field on the existing rollup tree payload.

Existing clients that ignore unknown child fields remain compatible. Product detail rollup summary only returns `summary`, not the full child tree, so that summary surface is unchanged.

## 7. Review Checklist

| # | Check |
|---|---|
| 1 | Child result exposes `uom` next to `quantity` and `line_weight` |
| 2 | UOM is normalized through existing BOMService helper |
| 3 | Missing UOM defaults to `EA` |
| 4 | Same child with different UOM relationships is not collapsed |
| 5 | No UOM conversion or rollup math change |
| 6 | No schema / scheduler / 142 runtime changes |

## 8. Follow-Up

The legacy report flattened BOM follow-up is closed by `DEV_AND_VERIFICATION_REPORT_BOM_FLATTEN_UOM_BUCKETS_20260421.md`.

Still open as a separate read/reporting increment:

- `BaselineService.compare_baselines()` snapshots do not carry UOM buckets

Baseline snapshots have broader downstream compatibility impact than this additive rollup tree field.
