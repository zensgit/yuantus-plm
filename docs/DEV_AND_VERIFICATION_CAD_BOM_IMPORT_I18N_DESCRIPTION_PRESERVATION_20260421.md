# CAD BOM Import I18N Description Preservation - Development And Verification

Date: 2026-04-21

## 1. Goal

Close the import-side follow-up from `DEV_AND_VERIFICATION_PRODUCT_DESCRIPTION_I18N_HELPER_20260421.md`.

Before this increment, `CadBomImportService` flattened all CAD node descriptions through `_normalize_text()`. If a source CAD BOM payload supplied a language map, such as:

```json
{"description": {"zh_CN": "内六角螺栓", "en_US": "Hex bolt"}}
```

the importer could stringify the dict instead of preserving localized text for the locale helper.

After this increment:

- dict language maps are detected and normalized;
- `description_i18n` / `name_i18n` are preserved in `Item.properties`;
- scalar `description` / `name` fallbacks remain present for legacy readers;
- `LocaleService.resolve_localized_property()` can resolve the imported maps.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/services/cad_bom_import_service.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_PRODUCT_DESCRIPTION_I18N_HELPER_20260421.md`

Not changed:

- no schema or migration;
- no writes to `meta_translations`;
- no auto-translation provider integration;
- no locale API/router change;
- no product detail/search response mutation;
- no CAD connector protocol change.

## 3. Implementation

### 3.1 Localized Map Normalization

New helper:

```python
_normalize_localized_text_map(value)
```

It accepts dict values only, strips language keys and text values, filters blank translations, and returns `None` when no usable localized text remains.

### 3.2 Source Shapes

The importer now recognizes these source shapes:

- direct field map: `description = {"zh_CN": "..."}`
- sidecar map: `description_i18n = {"zh_CN": "..."}`
- sidecar translations: `description_translations = {"zh_CN": "..."}`
- nested bucket: `i18n.description`
- nested translations bucket: `translations.description`

The same pattern is supported for `name`.

### 3.3 Backward-Compatible Fallbacks

For localized maps, the importer writes sidecar fields:

```json
{
  "description": "Hex bolt",
  "description_i18n": {"zh_CN": "内六角螺栓", "en_US": "Hex bolt"}
}
```

The scalar fallback preference is:

```text
en_US -> en -> zh_CN -> zh -> first map value
```

This keeps legacy scalar consumers working while enabling locale-aware consumers to resolve the localized value.

## 4. Tests

Focused verification:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py
```

Observed result:

```text
25 passed, 1 warning
```

Static check:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/cad_bom_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py
```

Observed result:

```text
pass
```

The warning is the existing relationship model deprecation emitted by bootstrap import.

Adjacent locale / doc-index regression:

```bash
YUANTUS_AUTH_MODE=optional \
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed result:

```text
51 passed, 1 warning
```

`YUANTUS_AUTH_MODE=optional` is required for the existing local locale router tests in this checkout.

## 5. Added Coverage

- `_normalize_localized_text_map()` filters empty values and rejects non-dicts.
- Direct dict `description` writes `description_i18n` and a scalar fallback.
- Nested `i18n.description` preserves scalar `description` unchanged.
- `name_i18n` writes a scalar `name` fallback and remains resolvable.
- Pure scalar `description` does not create an i18n sidecar.
- Imported properties are verified with `resolve_localized_property()`.

## 6. Compatibility

This is an additive import behavior change.

Legacy behavior preserved:

- scalar descriptions remain scalar;
- item numbers, BOM line aggregation, UOM normalization, refdes merge, and BOM writes are unchanged.

Intentional new behavior:

- localized source maps are no longer stringified;
- sidecar `description_i18n` / `name_i18n` may appear in imported `Item.properties`.

## 7. Review Checklist

| # | Check |
|---|---|
| 1 | No schema / migration was added |
| 2 | No writes to `meta_translations` |
| 3 | Dict descriptions are not converted through `str(dict)` |
| 4 | Scalar fallback remains available for legacy readers |
| 5 | Locale helper can resolve imported maps |
| 6 | Existing CAD BOM dedup and UOM tests remain green |
| 7 | No scheduler / shared-dev 142 runtime changes |

## 8. Follow-Up

The `Product Description I18N Helper` import-side follow-up is closed for CAD BOM import.

Separate future work, if needed:

- add connector-level examples for STEP/IGES metadata that emits `description_i18n`;
- report-level language selection;
- translation provider / auto-translation integration.
