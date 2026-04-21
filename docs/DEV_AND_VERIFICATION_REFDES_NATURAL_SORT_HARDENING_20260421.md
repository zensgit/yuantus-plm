# Refdes Natural Sort Hardening Delivery

Date: 2026-04-21

## 1. Goal

Harden the CAD BOM import refdes natural-sort increment after review found edge cases that were not pinned by tests.

This delivery keeps the existing scope: refdes emit ordering only. It does not change BOM relationship uniqueness, CAD profile, scheduler, schema, router, or shared-dev runtime behavior.

## 2. Implementation

`_natural_refdes_sort_key()` now uses deterministic numeric chunk tie-breakers:

- numeric value
- numeric chunk length
- original numeric chunk text

That makes tokens such as `R2` and `R02` stable without merging exact-token variants.

The existing exact-token behavior is preserved:

- `R2` and `R02` remain distinct tokens
- case variants remain distinct tokens
- no case normalization is introduced

## 3. Tests

Focused command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py
```

Result:

```text
29 passed, 1 warning in 0.61s
```

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
59 passed, 1 warning in 0.56s
```

Full `meta_engine` regression:

```bash
YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest -q src/yuantus/meta_engine/tests
```

Result:

```text
289 passed in 69.21s (0:01:09)
```

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py
git diff --check
```

Result: pass.

Added coverage:

- `test_join_refdes_tokens_orders_multiple_numeric_chunks_naturally`
- `test_join_refdes_tokens_keeps_leading_zero_tokens_deterministic`
- `test_join_refdes_tokens_keeps_case_variants_distinct`
- `test_import_bom_natural_sorts_refdes_tokens_across_duplicate_edges`

## 4. Acceptance

| Check | Status |
| --- | --- |
| `R10` sorts after `R2` | Pass |
| multi-number tokens like `J1A10` sort after `J1A2` | Pass |
| leading-zero variants keep exact token identity | Pass |
| case variants keep exact token identity | Pass |
| duplicate-edge import path emits natural-sorted refdes | Pass |

## 5. Compatibility

This is an ordering-only tightening for CAD BOM import aggregation output. It changes only the deterministic order of comma-joined `refdes` strings.

No response fields, schemas, routers, or persistence models changed.
