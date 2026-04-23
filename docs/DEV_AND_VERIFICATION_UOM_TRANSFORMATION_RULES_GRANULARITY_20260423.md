# DEV AND VERIFICATION: UOM Transformation Rules Granularity

Date: 2026-04-23

## 1. Goal

Close the remaining UOM-aware semantic edge in EBOM-to-MBOM transformation rules by adding optional `(item_id, uom)` bucket rules while preserving existing item-id-wide `exclude_items` and `substitute_items` behavior.

## 2. Scope

Runtime change:

- `src/yuantus/meta_engine/manufacturing/mbom_service.py`

Test change:

- `src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py`

Supported rules after this change:

| Rule | Existing / New | Shape | Semantics |
| --- | --- | --- | --- |
| `exclude_items` | existing | `["ITEM"]` | Exclude all UOM variants for the item. |
| `substitute_items` | existing | `{"ITEM": "SUB"}` | Substitute all UOM variants for the item. |
| `exclude_item_uom_buckets` | new | `["ITEM::UOM"]` | Exclude only the matching normalized UOM variant. |
| `substitute_item_uom_buckets` | new | `{"ITEM::UOM": "SUB"}` | Substitute only the matching normalized UOM variant. |

Bucket format:

```text
<item_id>::<normalized_uom>
```

The UOM side uses `_normalize_bom_uom()`, so `" mm "`, `"mm"`, and `"MM"` all resolve to `MM`. Missing or empty UOM resolves to `EA`, matching the existing BOM default. Configured bucket strings are normalized as well, so `" ITEM :: mm "` and `"ITEM::MM"` resolve to the same bucket.

## 3. Implementation

Added helper functions in `mbom_service.py`:

- `_item_uom_bucket_key(item_id, uom)`
- `_normalize_item_uom_bucket(value)`
- `_normalize_item_uom_bucket_set(values)`
- `_normalize_item_uom_bucket_map(mapping)`

In `_transform_ebom_to_mbom()`:

- Compute the child relationship UOM before exclude/substitute decisions.
- Exclude a child if `child_id in exclude_items` or `child_id::uom in exclude_item_uom_buckets`.
- Choose a substitute by checking `substitute_item_uom_buckets[child_id::uom]` first, then falling back to `substitute_items[child_id]`.
- Keep existing phantom collapse, scrap, quantity, and recursive transformation behavior unchanged.

Precedence:

- Broad `exclude_items` still excludes all variants and cannot be overridden by bucket rules.
- UOM-specific substitute overrides broad `substitute_items` for the matching bucket.
- Broad `substitute_items` remains the fallback for all variants without a bucket-specific substitute.

## 4. Tests

Added focused tests:

- `_item_uom_bucket_key()` normalizes UOM and rejects empty item IDs.
- `_normalize_item_uom_bucket()` normalizes configured bucket strings.
- `exclude_item_uom_buckets` excludes only the matching UOM variant.
- `substitute_item_uom_buckets` substitutes only the matching UOM variant.
- Configured bucket text is normalized before matching.
- `substitute_item_uom_buckets` overrides broad `substitute_items` for the matching UOM while broad substitute still applies to the other variants.

Existing transformation test still covers:

- Legacy `exclude_items`.
- Legacy `substitute_items`.
- Phantom collapse.
- Scrap-rate path.

## 5. Verification

Executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/manufacturing/mbom_service.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py
```

Result: passed.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py
```

Result: `10 passed`.

After adding configured-bucket normalization:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py
```

Result: `12 passed`.

Executed:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_release.py \
  src/yuantus/meta_engine/tests/test_report_service_bom_uom.py \
  src/yuantus/meta_engine/tests/test_baseline_enhanced.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `44 passed, 1 warning`.

An earlier broader command included `test_manufacturing_mbom_router.py` and failed with 5 known `401 Unauthorized` auth-mode test hygiene failures. That file was excluded from the final signal because this PR changes only MBOM transformation service semantics and does not touch router auth behavior.

Executed:

```bash
git diff --check
```

Result: passed.

## 6. Non-Goals

- No schema or migration changes.
- No UI changes.
- No scheduler or shared-dev 142 interaction.
- No change to existing item-id-wide rule behavior.
- No change to the existing transformed item identity behavior in legacy substitute handling.
- No expansion into MES, sales, procurement, or routing-rule DSLs.

## 7. Status

Implementation and focused verification are complete.
