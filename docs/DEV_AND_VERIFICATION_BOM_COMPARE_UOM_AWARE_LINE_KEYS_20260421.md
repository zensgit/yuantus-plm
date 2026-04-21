# BOM Compare UOM-Aware Line Keys Delivery

Date: 2026-04-21

## 1. Goal

Close the comparison-side follow-up after allowing multiple BOM lines for the same `(parent, child)` with different `uom`.

Before this increment, summarized BOM compare could aggregate quantities across different units and return a `MIXED` UOM bucket. That is unsafe after UOM-specific BOM lines are allowed.

After this increment:

- core `BOMService` summarized compare groups by `(child config, normalized UOM)`
- core `BOMService` by-item compare groups by `(child item id, normalized UOM)`
- core line-level keys such as find number, refdes, quantity, and `line_full` include normalized UOM
- plugin compare summarized mode uses the same UOM-aware bucket
- plugin diffs expose `uom_a` / `uom_b` for operator visibility

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/bom_service.py`
- `plugins/yuantus-bom-compare/main.py`
- `src/yuantus/meta_engine/tests/test_plugin_bom_compare.py`
- `docs/DEV_AND_VERIFICATION_BOM_IMPORT_DEDUP_AGGREGATION_20260421.md`
- `docs/DEV_AND_VERIFICATION_BOM_UOM_AWARE_DUPLICATE_GUARD_20260421.md`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- schema / migrations
- BOM duplicate guard storage semantics
- where-used APIs
- CAD import aggregation
- scheduler / shared-dev 142 runtime

## 3. Implementation

### 3.1 Core BOMService

`BOMService.COMPARE_MODES` now resolves:

- `summarized` -> `line_key="child_config_uom"`
- `by_item` -> `line_key="child_id_uom"`

New line-key variants:

- `child_config_uom`
- `child_id_uom`

`line_full` also includes normalized UOM so fully keyed comparisons do not collapse two lines that differ only by unit.

Line-level modes also include normalized UOM:

- `child_id_find_num`
- `child_config_find_num`
- `child_id_refdes`
- `child_config_refdes`
- `child_id_find_refdes`
- `child_config_find_refdes`
- `child_id_find_num_qty`
- `child_config_find_num_qty`

### 3.2 Plugin Compare

`plugins/yuantus-bom-compare` now:

- accepts `uom_key` with default `"uom"`
- normalizes blank/missing UOM to `EA`
- includes UOM in summarized / num_qty / by_position / by_reference keys
- emits `uom_a` and `uom_b` in response/export rows

`only_product` intentionally remains child-only because that mode ignores relationship quantity semantics by design.

## 4. Tests

Focused command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py
```

Result:

```text
35 passed, 1 warning in 0.89s
```

Additional validation was run after the documentation update:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
58 passed, 1 warning in 1.38s
```

Note: auth-bound router tests were not used as the validation gate for this service/plugin increment. In this local invocation those routes return HTTP 401 without test auth overrides, which is outside this change scope.

## 5. Added Coverage

- `test_core_summarized_compare_keeps_different_uom_quantities_separate`
- `test_core_summarized_compare_reports_uom_bucket_add_remove`
- `test_core_line_keys_include_uom_for_line_level_modes`
- `test_plugin_summarized_compare_keeps_different_uom_quantities_separate`
- `test_plugin_summarized_compare_reports_uom_bucket_add_remove`
- `test_plugin_line_keys_include_uom_for_line_level_modes`

These tests pin the critical behavior:

- `EA` and `MM` lines for the same child do not collapse into one quantity bucket
- only the changed UOM bucket is reported as modified
- UOM bucket replacement appears as remove + add, not one synthetic mixed row
- unchanged UOM bucket remains unchanged
- line-level key modes include normalized UOM

## 6. Compatibility

This is an intentional semantic tightening for summarized/by-item compare. Existing same-UOM aggregation behavior is preserved.

The visible behavior change is that different UOMs now produce separate line keys instead of one `MIXED` UOM row. That is the safer behavior after BOM storage itself supports UOM-specific duplicate lines.

## 7. Review Checklist

| # | Check |
|---|---|
| 1 | `summarized` resolves to `child_config_uom` |
| 2 | `by_item` resolves to `child_id_uom` |
| 3 | Missing plugin UOM defaults to `EA` |
| 4 | Plugin summarized mode separates same child with `EA` vs `MM` |
| 5 | `only_product` remains child-only |
| 6 | Line-level find/refdes/quantity keys include UOM |
| 7 | No schema / scheduler / 142 runtime changes |

## 8. Follow-Up

No immediate follow-up is required for the UOM compare path.

If product later wants UOM synonyms such as `EACH` -> `EA`, that should be implemented through a tenant-level UOM dictionary, not hardcoded inside compare logic.
