# Design: ECO Compute Changes Compare Mode

## Date

2026-04-05

## Goal

Close the primary implementation gap from `ECO BOM Compare Mode Integration Audit`
by making `POST /eco/{eco_id}/compute-changes` compare-mode aware.

## Scope

Files changed:

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`
- `src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py`

## Implementation

### 1. Router contract

`POST /eco/{eco_id}/compute-changes` now accepts optional `compare_mode` with
the same mode family already exposed on BOM compare and ECO BOM diff surfaces:

- `only_product`
- `summarized`
- `by_item`
- `num_qty`
- `by_position`
- `by_reference`
- `by_find_refdes`

No existing caller is broken because the parameter is optional.

### 2. Service behavior

`ECOService.compute_bom_changes()` now supports:

- legacy path when `compare_mode` is not provided
- compare-aware path when `compare_mode` is provided

Compare-aware path:

1. calls `get_bom_diff(eco_id, max_levels=1, compare_mode=...)`
2. maps compare diff entries into `ECOBOMChange` rows
3. preserves existing `ECOBOMChange` persistence contract

### 3. Mapping strategy

For compare-aware change creation:

- `added` -> `change_type="add"`
- `removed` -> `change_type="remove"`
- `changed` -> `change_type="update"`

Mapping fields:

- `relationship_id` -> `relationship_item_id`
- `parent_id` -> `parent_item_id`
- `child_id` -> `child_item_id`
- add/remove use compare entry `properties`
- update uses `before_line` / `after_line` when available, with `before` / `after`
  as fallback

### 4. Compatibility

- existing callers that omit `compare_mode` keep the previous level-1 behavior
- invalid compare modes continue to raise `ValueError` and map to router `400`
- no schema change or migration is required

## Out of Scope

- compare-mode-specific apply/apply-diagnostics changes
- new ECO export surfaces
- broader ECO compare-mode reading guide/final-summary docs

## Result

The main functional gap from the audit is closed:

- `compute-changes` can now participate in the same compare-mode contract family
  as BOM compare and ECO read-side diff/impact surfaces
