# Product Description I18N Helper - Development And Verification

Date: 2026-04-21

## 1. Goal

Close the product-description half of gap analysis `§一.6 BOM 去重汇总 + 产品描述多语言` without adding schema or expanding into report auto-translation.

This increment adds a bounded helper for Item/product localized text:

- reuse existing `meta_translations` as the authoritative translation table;
- support inline `Item.properties` language maps for lightweight product data;
- provide a read-only locale endpoint to resolve `name` / `description` and other requested fields;
- keep existing product detail/search payloads unchanged.

## 2. Scope

Changed:

- `src/yuantus/meta_engine/locale/service.py`
- `src/yuantus/meta_engine/web/locale_router.py`
- `src/yuantus/meta_engine/tests/test_locale_service.py`
- `src/yuantus/meta_engine/tests/test_locale_router.py`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- no database schema or migration;
- no auto-translation provider integration;
- no report-language helper expansion;
- no product detail payload mutation;
- no search indexing behavior change.

## 3. Resolution Order

For each requested Item field, the service resolves in this order:

| Order | Source | Example |
| --- | --- | --- |
| 1 | `meta_translations` row | `(record_type=item, record_id, field_name=description, lang=zh_CN)` |
| 2 | direct property language map | `properties["description"] = {"zh_CN": "..."}` |
| 3 | sidecar i18n property | `properties["description_i18n"] = {"zh_CN": "..."}` |
| 4 | sidecar translations property | `properties["description_translations"] = {"zh_CN": "..."}` |
| 5 | nested i18n bucket | `properties["i18n"]["description"]["zh_CN"]` |
| 6 | nested translations bucket | `properties["translations"]["description"]["zh_CN"]` |
| 7 | scalar fallback | `properties["description"] = "Hex bolt"` |

The table row wins over inline properties. This keeps centralized translation workflows authoritative while allowing CAD/import callers to carry lightweight inline maps.

## 4. API

New endpoint:

```text
GET /api/v1/locale/items/{item_id}/localized-fields
```

Query parameters:

| Parameter | Required | Notes |
| --- | --- | --- |
| `lang` | yes | primary language, e.g. `zh_CN` |
| `fields` | no | repeatable or comma-separated; default `name,description` |
| `fallback_langs` | no | repeatable or comma-separated fallback chain |

Example:

```bash
curl "$BASE_URL/api/v1/locale/items/part-1/localized-fields?lang=zh_CN&fields=name,description&fallback_langs=en_US"
```

Response shape:

```json
{
  "record_type": "item",
  "record_id": "part-1",
  "lang": "zh_CN",
  "fallback_langs": ["en_US"],
  "resolved": [
    {
      "field": "description",
      "lang": "en_US",
      "value": "Hex bolt",
      "source": "properties_i18n",
      "chain": []
    }
  ],
  "missing": [],
  "fallbacks_used": ["en_US"]
}
```

## 5. Verification

Focused verification:

```bash
YUANTUS_AUTH_MODE=optional \
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py
```

Observed result:

```text
23 passed
```

Adjacent product/search/doc-index regression:

```bash
YUANTUS_AUTH_MODE=optional \
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_product_detail_service.py \
  src/yuantus/meta_engine/tests/test_product_detail_cockpit_extensions.py \
  src/yuantus/meta_engine/tests/test_search_service_fallback.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed result:

```text
33 passed
```

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/locale/service.py \
  src/yuantus/meta_engine/web/locale_router.py
```

Observed result:

```text
pass
```

## 6. Acceptance Criteria

| Criterion | Status |
| --- | --- |
| Translation table wins over inline property maps | Pass |
| `description_i18n` primary/fallback language maps resolve | Pass |
| Direct `description={lang:value}` maps resolve | Pass |
| Scalar `description` remains fallback-compatible | Pass |
| Missing fields are reported, not silently dropped | Pass |
| Router supports comma-separated `fields` and `fallback_langs` | Pass |
| Missing item returns 404 | Pass |
| Existing locale translation/report endpoints remain green | Pass |

## 7. Boundary

This is not auto-translation and not report localization. It is the product/Item field helper needed before any UI or import pipeline can safely expose multilingual product descriptions.

The CAD BOM import follow-up is closed by `DEV_AND_VERIFICATION_CAD_BOM_IMPORT_I18N_DESCRIPTION_PRESERVATION_20260421.md`.
The report-level language selection follow-up is closed by `DEV_AND_VERIFICATION_REPORT_LANGUAGE_SELECTION_20260421.md`.

Remaining separate future work:

- translation provider / auto-translation integration.
