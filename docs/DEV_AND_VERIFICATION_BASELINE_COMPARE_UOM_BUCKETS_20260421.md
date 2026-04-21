# Baseline Compare UOM Buckets Delivery

Date: 2026-04-21

## 1. Goal

Close the remaining UOM read/reporting gap in the legacy baseline-to-baseline comparison endpoint.

Before this increment, `BaselineService.compare_baselines()` keyed item members only by `item_id`. When the same child item existed as separate BOM lines with different UOMs, the comparison could collapse those lines into one item bucket.

After this increment:

- baseline comparison derives normalized UOM from frozen baseline snapshots
- newly populated BOM item members bind the source `relationship_id` for exact line lookup
- item comparison keys become UOM-aware when snapshot line UOM is available
- added/removed/changed details expose `uom` and `bucket_key`
- old baseline members without snapshot UOM still fall back to legacy comparison behavior

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/baseline_service.py`
- `src/yuantus/meta_engine/tests/test_baseline_enhanced.py`
- `docs/DELIVERY_DOC_INDEX.md`

Documentation follow-up updates:

- `docs/DEV_AND_VERIFICATION_BOM_ROLLUP_UOM_CHILD_VISIBILITY_20260421.md`
- `docs/DEV_AND_VERIFICATION_REPORT_BOM_FLATTEN_UOM_BUCKETS_20260421.md`
- `docs/DEV_AND_VERIFICATION_WHERE_USED_UOM_EXPORT_COLUMNS_20260421.md`

Not changed:

- baseline schema / migrations
- baseline snapshot creation format
- BOM write paths
- router contracts
- scheduler / shared-dev 142 runtime

## 3. Implementation

### 3.1 Snapshot UOM Lookup

`BaselineService` now builds a per-baseline lookup from `Baseline.snapshot.children[*].relationship.properties.uom`.

Lookup keys:

- `(item_id, member.path)` for exact item member matching
- `relationship_id` for relationship members
- `item_id` fallback only when an item has a single unambiguous UOM in that snapshot

UOM normalization reuses the existing BOM helper `_normalize_bom_uom()`, so missing UOM defaults to `EA` and strings are upper-cased.

### 3.2 Relationship Binding

`_add_item_member()` now accepts an optional `relationship_id`, and `_add_bom_members()` passes the BOM relationship id when creating child item members.

This uses the existing nullable `BaselineMember.relationship_id` column. No schema change is needed.

The binding matters for same-parent/same-child BOM lines with different UOMs: their member paths can be identical, but their relationship ids remain distinct.

### 3.3 Compare Key

Item members now compare as:

```text
("item", item_id, normalized_uom)
```

when UOM is available from the frozen snapshot.

Members without snapshot UOM keep the previous key:

```text
("item", item_id)
```

This keeps old baseline data compatible while allowing newly captured UOM-aware snapshots to compare correctly.

### 3.4 Detail Rows

For item rows with UOM, comparison details now include:

- `uom`
- `bucket_key`, formatted as `reference_id::UOM`

Legacy fields are preserved:

- `member_type`
- `reference_id`
- `item_number`
- `revision`
- `baseline_a`
- `baseline_b`

CSV export already derives columns dynamically from detail rows, so `uom` and `bucket_key` flow through without a router change.

## 4. Tests

Focused command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_baseline_enhanced.py
```

Result:

```text
12 passed in 0.20s
```

Static check:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/baseline_service.py \
  src/yuantus/meta_engine/tests/test_baseline_enhanced.py
```

Result:

```text
passed
```

## 5. Added Coverage

- `test_compare_baselines_keeps_same_item_different_uom_separate`
- `test_compare_baselines_uses_relationship_id_when_same_path_has_multiple_uoms`
- `test_compare_baselines_normalizes_same_uom_bucket`
- `test_compare_baselines_defaults_missing_snapshot_uom_to_ea`
- `test_compare_baselines_changed_row_exposes_uom_bucket`
- export regression now asserts `uom` and `bucket_key` can flow into CSV output

These tests pin the critical behavior:

- same item with `EA` and `MM` becomes add/remove, not one collapsed item row
- same-path multi-UOM members resolve through relationship id instead of path alone
- `" ea "` and `"EA"` normalize to the same bucket
- missing snapshot UOM defaults to `EA`
- changed rows keep `reference_id=item_id` and add UOM bucket metadata

## 6. Compatibility

This is a semantic tightening for baseline comparisons.

Additive fields:

- `uom`
- `bucket_key`

Intentional behavior change:

- UOM-aware baseline snapshots may produce different summary counts when the same item exists in multiple UOM buckets.

Compatibility guard:

- members without snapshot UOM continue using the legacy item-only key.

## 7. Review Checklist

| # | Check |
|---|---|
| 1 | No schema or migration was added |
| 2 | UOM is read from frozen snapshot, not live BOM state |
| 3 | BOM item members bind their source relationship id |
| 4 | UOM normalization reuses `_normalize_bom_uom()` |
| 5 | Same item with different UOM does not collapse |
| 6 | Same-path multi-UOM members remain distinguishable |
| 7 | Same item with normalized same UOM still compares unchanged |
| 8 | Missing UOM defaults to `EA` when the snapshot line exists |
| 9 | Existing legacy compare test still passes |
| 10 | CSV export carries additive `uom` and `bucket_key` fields |

## 8. Follow-Up

The known UOM read/reporting gap tracked by the adjacent where-used, rollup, and report delivery docs is closed for `BaselineService.compare_baselines()`.

Remaining separate work, if needed later:

- Persist UOM directly on `BaselineMember` through a schema migration.
- Add E2E coverage to `scripts/verify_baseline_e2e.sh` with same child item in multiple UOMs.
