# Report Language Selection - Development And Verification

Date: 2026-04-21

## 1. Goal

Close the read-only report/export follow-up after product description i18n and CAD BOM import i18n preservation.

This increment lets report search and report-definition export resolve item `name` / `description` from inline multilingual property maps such as:

```json
{
  "name": "Bolt",
  "name_i18n": {"zh_CN": "Bolt CN"},
  "description": "Hex bolt",
  "description_i18n": {"zh_CN": "Hex bolt CN", "en_US": "Hex bolt"}
}
```

## 2. Scope

Changed:

- `src/yuantus/meta_engine/reports/search_service.py`
- `src/yuantus/meta_engine/reports/report_service.py`
- `src/yuantus/meta_engine/web/report_router.py`
- `src/yuantus/meta_engine/tests/test_reports_advanced_search.py`
- `src/yuantus/meta_engine/tests/test_report_router_permissions.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_PRODUCT_DESCRIPTION_I18N_HELPER_20260421.md`
- `docs/DEV_AND_VERIFICATION_CAD_BOM_IMPORT_I18N_DESCRIPTION_PRESERVATION_20260421.md`

Not changed:

- no schema or migration;
- no `meta_translations` writes;
- no translation provider or auto-translation;
- no report template engine;
- no scheduler or shared-dev 142 behavior;
- no CAD connector contract change.

## 3. Runtime Contract

`AdvancedSearchService.search()` now accepts three optional read-only parameters:

| Parameter | Meaning |
| --- | --- |
| `lang` | Primary language to resolve |
| `fallback_langs` | Ordered fallback chain |
| `localized_fields` | Fields to localize; defaults to `name` and `description` when `lang` is set |

`POST /api/v1/reports/search` accepts the same optional fields.

Report definitions pass the same fields through `data_source` or request `parameters` because `_execute_data_source()` merges both before delegating to `AdvancedSearchService.search()`.

Example report definition data source:

```json
{
  "type": "query",
  "item_type_id": "Part",
  "columns": ["name", "description", "weight"],
  "lang": "zh_CN",
  "fallback_langs": ["en_US"],
  "localized_fields": ["name", "description"]
}
```

## 4. Resolution Rules

The implementation reuses `locale.service.resolve_localized_property()`.

Resolution order is unchanged from the product helper:

1. direct property map, for example `description={"zh_CN": "..."}`
2. sidecar map, for example `description_i18n`
3. sidecar translations map, for example `description_translations`
4. nested `i18n.description`
5. nested `translations.description`
6. scalar fallback, for example `description="Hex bolt"`

The report layer only replaces the emitted row value for selected fields. It does not add localization metadata columns by default.

## 5. Compatibility

Existing callers are unchanged unless they pass `lang`.

When `lang` is omitted:

- report search output is identical to the previous path;
- CSV / JSON export payload generation is unchanged;
- saved searches without language criteria are unchanged.

When `lang` is present:

- `name` and `description` are localized by default;
- callers can narrow the set with `localized_fields`;
- unresolved fields keep scalar fallback behavior through `resolve_localized_property()`.

## 6. Verification

Focused tests:

```bash
YUANTUS_AUTH_MODE=optional \
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_reports_advanced_search.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py
```

Observed:

```text
13 passed
```

Adjacent locale/import/report/doc-index regression:

```bash
YUANTUS_AUTH_MODE=optional \
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_reports_advanced_search.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed:

```text
64 passed, 1 warning
```

Broader report/report-locale regression:

```bash
YUANTUS_AUTH_MODE=optional \
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_reports_advanced_search.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py \
  src/yuantus/meta_engine/tests/test_report_service_bom_uom.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed:

```text
83 passed, 1 warning
```

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/reports/search_service.py \
  src/yuantus/meta_engine/reports/report_service.py \
  src/yuantus/meta_engine/web/report_router.py \
  src/yuantus/meta_engine/tests/test_reports_advanced_search.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py

git diff --check
```

Observed:

```text
pass
```

## 7. Acceptance Criteria

| Criterion | Status |
| --- | --- |
| Advanced search can localize `name` and `description` by `lang` | Pass |
| `fallback_langs` is forwarded to the locale helper | Pass |
| `localized_fields` can narrow which fields are replaced | Pass |
| Requested columns are preserved; unrequested localized fields are not added | Pass |
| Requested fields can be populated from `*_i18n` sidecars even without scalar values | Pass |
| Report definition query data source forwards language selection | Pass |
| Router accepts optional language selection fields | Pass |
| CSV / JSON export code path stays shared with report-definition query data | Pass |
| No schema, provider, or scheduler change | Pass |

## 8. Boundary

This closes report-level language selection for existing search/report-definition export rows.

It does not close:

- automatic translation provider integration;
- report template localization;
- per-tenant UOM synonym dictionaries;
- connector-level examples for STEP/IGES metadata payloads.
