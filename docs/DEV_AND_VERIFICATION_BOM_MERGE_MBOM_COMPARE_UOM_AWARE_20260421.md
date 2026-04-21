# BOM Merge + MBOM Compare UOM-Aware Delivery

Date: 2026-04-21

## 1. Goal

Close the remaining UOM-aware cascade gaps after same `(parent, child)` BOM lines with different `uom` became valid.

This increment fixes two concrete correctness risks:

- `BOMService.merge_bom()` no longer matches target lines by `child_id` only.
- `MBOMService.compare_ebom_mbom()` no longer flattens EBOM/MBOM structures by `item_id` only.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/manufacturing/mbom_service.py`
- `src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py`
- `src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- schema / migrations
- BOM duplicate guard semantics
- MBOM transformation rule schema
- scheduler / 142 runtime
- UI / API shape beyond additive compare fields

## 3. Implementation

### 3.1 BOM merge

`merge_bom()` now builds the target relationship map by `(related_id, normalized_uom)` instead of `related_id`.

Source relationship properties are normalized before lookup:

```python
normalized_uom = _normalize_bom_uom(props.get("uom"))
props["uom"] = normalized_uom
bom_line_key = (child_id, normalized_uom)
```

This prevents a source `child/uom=EA` row from overwriting a target `child/uom=MM` row, and allows missing UOM variants to be added as distinct relationship lines.

### 3.2 MBOM compare

`compare_ebom_mbom()` now compares flattened buckets keyed by `item_id::UOM`.

Each flattened row includes:

- `item_id`
- `bucket_key`
- `uom`
- `quantity`
- `level`
- `item`

Diff rows preserve legacy `item_id` and add `bucket_key` / `uom` for operator and downstream visibility.

### 3.3 Excluded observation

`_transform_ebom_to_mbom()` still interprets `exclude_items` and `substitute_items` by `item_id`. That is intentionally left unchanged: those rules currently mean "exclude/replace this part" rather than "exclude/replace this UOM-specific BOM line". UOM-granular transformation rules require a separate schema decision.

## 4. Tests

Focused command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py
```

Result:

```text
13 passed, 1 warning in 0.94s
```

Adjacent regression:

```bash
YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_report_service_bom_uom.py \
  src/yuantus/meta_engine/tests/test_baseline_enhanced.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_release.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py \
  src/yuantus/meta_engine/tests/test_scheduler_bom_to_mbom_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
95 passed, 1 warning in 1.48s
```

Full `meta_engine` regression:

```bash
YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest -q src/yuantus/meta_engine/tests
```

Result:

```text
289 passed in 70.41s (0:01:10)
```

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/bom_service.py \
  src/yuantus/meta_engine/manufacturing/mbom_service.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py
git diff --check
```

Result: pass.

The focused tests cover:

- merge updates the matching UOM bucket without overwriting another UOM bucket
- merge adds a missing UOM variant instead of collapsing by child id
- EBOM/MBOM compare keeps same item with different UOMs separate
- UOM replacement reports add/remove buckets instead of a synthetic quantity change
- flattening uses relationship UOM/quantity from EBOM child entries
- flattening also accepts relationship top-level `quantity/uom` for compatibility

## 5. Compatibility

`BOMService.merge_bom()` keeps the same public signature and return shape.

`MBOMService.compare_ebom_mbom()` keeps the existing top-level lists and `item_id` in quantity diffs. The only visible change is additive metadata (`bucket_key`, `uom`) and corrected bucket semantics for same item / different UOM.

## 6. Acceptance

| Check | Status |
| --- | --- |
| F1 merge no longer uses child-only target map | Pass |
| F1 merge cannot silently overwrite another UOM line | Pass |
| F1 missing UOM variant is added as a separate line | Pass |
| F2 compare no longer flattens by item_id only | Pass |
| F2 compare exposes `bucket_key` and `uom` | Pass |
| F3 transformation rule schema left out of scope | Pass |

## 7. Follow-Up

No immediate follow-up is required for F1/F2.

If product needs UOM-specific MBOM transformation rules, define a new rule schema separately; do not overload the current `exclude_items` / `substitute_items` item-id semantics.
