# Refdes Natural Sort Delivery

Date: 2026-04-21

## 1. Goal

Close the known follow-up from `DEV_AND_VERIFICATION_BOM_IMPORT_DEDUP_AGGREGATION_20260421.md`: CAD BOM import refdes aggregation should sort engineering reference designators naturally.

Before this increment, `_join_refdes_tokens(["R10", "R2", "R1"])` emitted `R1,R10,R2` because it used plain lexicographic sort.

After this increment, it emits `R1,R2,R10`.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/cad_bom_import_service.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- `BOMService.add_child`
- `BOMService.get_bom_line_by_parent_child`
- BOM uniqueness semantics for same `(parent, child)` with different `uom`
- scheduler / CAD profile / shared-dev 142 scripts
- schema or migration files

## 3. Implementation

Added `_natural_refdes_sort_key()` to split each refdes token into text and numeric chunks.

Examples:

- `R1`, `R2`, `R10` now sort as `R1,R2,R10`
- `C2`, `C10`, `R1`, `R10` now sort as `C2,C10,R1,R10`

Dedup remains exact-token based. This increment does not normalize case or alter stored token text.

## 4. Tests

Focused command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py
```

Result:

```text
20 passed, 1 warning in 0.62s
```

Static compile:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/cad_bom_import_service.py
```

Result: passed.

Adjacent regression + doc-index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_suspended_write_paths.py \
  src/yuantus/meta_engine/tests/test_numbering_service.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
50 passed, 1 warning in 0.55s
```

Diff hygiene:

```bash
git diff --check
```

Result: passed.

## 5. Added / Updated Test Coverage

- `test_join_refdes_tokens_natural_sorts_and_deduplicates`
- `test_join_refdes_tokens_orders_numeric_chunks_naturally`
- `test_import_bom_sorts_single_edge_comma_separated_refdes`

The import test now pins a single-edge payload of `R10,R1,R2,R1` to `R1,R2,R10`.

## 6. Compatibility

This is an intentional ordering-only change for emitted `refdes` strings during CAD BOM import aggregation.

The change is backward-compatible for API shape and result schema:

- no new response fields
- no removed response fields
- no migration
- no router change

Potential visible behavior: callers that previously observed lexicographic refdes ordering will now observe natural ordering.

## 7. Review Checklist

| # | Check |
|---|---|
| 1 | `R10` sorts after `R2`, not before |
| 2 | Prefix grouping remains deterministic (`C*` before `R*`) |
| 3 | Exact-token dedup behavior is unchanged |
| 4 | Empty / `None` tokens still return `None` through `_join_refdes_tokens` |
| 5 | CAD BOM import aggregation still merges duplicate edges as before |
| 6 | No BOM uniqueness semantics changed |
| 7 | No scheduler / CAD profile / 142 files touched |

## 8. Follow-Up

The separate medium-scope follow-up remains open: supporting two BOM lines with the same `(parent, child)` but different `uom` requires changing `BOMService.get_bom_line_by_parent_child` and related where-used / report assumptions. This increment deliberately does not touch that scope.
