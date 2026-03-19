# C6 – Locale & Report Locale Bootstrap

**Branch**: `feature/claude-c6-locale`
**Date**: 2026-03-18
**Status**: Implemented & Verified

---

## 1. Objective

Provide a locale-aware translation storage layer and a report locale profile
system so that PLM exports (BOM, ECO, quality reports) can be rendered in the
user's preferred language, number/date format, paper size, and timezone.

## 2. Odoo 18 Alignment

| Odoo 18 Concept | Yuantus Mapping |
|---|---|
| `ir.translation` | `meta_translations` – per-field, per-record, per-lang translations |
| Report paperformat | `meta_report_locale_profiles` – paper size, orientation, header/footer |
| `res.lang` settings | `lang`, `number_format`, `date_format`, `time_format`, `timezone` on profile |
| Module-scoped terms | `Translation.module` column for namespace isolation |

## 3. Domain Models

### 3.1 Translation (`meta_translations`)

| Column | Type | Description |
|---|---|---|
| id | String PK | UUID |
| record_type | String(120) | e.g. "item", "bom", "eco" |
| record_id | String | FK-style reference to source record |
| field_name | String(120) | e.g. "name", "description" |
| lang | String(10) | IETF locale code (e.g. "zh_CN") |
| source_value | Text (nullable) | Original value for reference |
| translated_value | Text | Translated string |
| state | String(30) | draft / approved / needs_review |
| module | String(120, nullable) | Namespace scope |
| properties | JSON/JSONB | Extensible metadata |

**Unique constraint**: `(record_type, record_id, field_name, lang)`

### 3.2 ReportLocaleProfile (`meta_report_locale_profiles`)

| Column | Type | Description |
|---|---|---|
| id | String PK | UUID |
| name | String(200) | Human-readable profile name |
| lang | String(10) | Target language |
| fallback_lang | String(10, nullable) | Fallback if key missing |
| number_format | String(50) | e.g. "#,##0.00" |
| date_format | String(50) | e.g. "YYYY-MM-DD", "YYYY年MM月DD日" |
| time_format | String(50) | e.g. "HH:mm:ss" |
| timezone | String(80) | e.g. "UTC", "Asia/Shanghai" |
| paper_size | String(20) | a4 / letter / legal / a3 |
| orientation | String(20) | portrait / landscape |
| header_text | Text (nullable) | Report header override |
| footer_text | Text (nullable) | Report footer override |
| logo_path | String (nullable) | Path to logo image |
| report_type | String(120, nullable) | Scope to specific report type |
| is_default | Boolean | Language-level default flag |
| properties | JSON/JSONB | Extensible metadata |

### 3.3 Enums

- **TranslationState**: `draft`, `approved`, `needs_review`
- **PaperSize**: `a4`, `letter`, `legal`, `a3`

## 4. Service Layer

### 4.1 LocaleService

| Method | Description |
|---|---|
| `upsert_translation(...)` | Create or update a translation by composite key |
| `get_translation(record_type, record_id, field_name, lang)` | Lookup single translation |
| `get_translations_for_record(record_type, record_id, lang?)` | All translations for a record |
| `get_translations_by_lang(lang, record_type?, module?, state?)` | Filter by language + optional scope |
| `bulk_upsert(entries)` | Batch create/update with summary stats |
| `delete_translation(record_type, record_id, field_name, lang)` | Remove single translation |

### 4.2 ReportLocaleService

| Method | Description |
|---|---|
| `create_profile(...)` | Create with paper_size/orientation validation |
| `get_profile(id)` | Lookup by ID |
| `list_profiles(lang?, report_type?, is_default?)` | Filtered listing |
| `resolve_profile(lang, report_type?)` | Cascading resolution: exact → lang default → global default |
| `update_profile(id, **fields)` | Partial update |
| `delete_profile(id)` | Remove profile |

**Resolution cascade** for `resolve_profile`:
1. Exact match on `lang` + `report_type`
2. Language default (`lang` + `is_default=True`)
3. Global default (`is_default=True`, any lang)

## 5. REST API

### 5.1 Translation Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/locale/translations` | Upsert single translation |
| POST | `/locale/translations/bulk` | Batch upsert |
| GET | `/locale/translations?record_type=&record_id=` | Get translations for record |
| GET | `/locale/translations/by-lang?lang=` | Filter by language |

### 5.2 Report Profile Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/locale/report-profiles` | Create profile |
| GET | `/locale/report-profiles` | List with optional filters |
| GET | `/locale/report-profiles/resolve?lang=` | Cascading resolution |
| GET | `/locale/report-profiles/{id}` | Get by ID |
| PATCH | `/locale/report-profiles/{id}` | Partial update |
| DELETE | `/locale/report-profiles/{id}` | Delete profile |

## 6. File Layout

```
src/yuantus/meta_engine/
├── locale/
│   ├── __init__.py
│   ├── models.py          # Translation, TranslationState
│   └── service.py         # LocaleService
├── report_locale/
│   ├── __init__.py
│   ├── models.py          # ReportLocaleProfile, PaperSize
│   └── service.py         # ReportLocaleService
├── web/
│   └── locale_router.py   # Combined REST endpoints
└── tests/
    ├── test_locale_service.py          # 8 tests
    └── test_report_locale_service.py   # 12 tests
```

## 7. Design Decisions

1. **Two sub-packages** (`locale/` + `report_locale/`): Separates translation
   storage (per-field strings) from report formatting configuration (paper,
   layout, number formats). Each has independent lifecycle.

2. **Composite unique key for translations**: `(record_type, record_id,
   field_name, lang)` enforced at DB level ensures one translation per
   field-language pair.

3. **Upsert semantics**: `upsert_translation` looks up by composite key first,
   updates if found, creates if not. `bulk_upsert` delegates per-row to the
   same logic with error collection.

4. **Profile resolution cascade**: Three-tier fallback (exact → lang default →
   global default) ensures a profile is always found when a global default
   exists, while still allowing per-report-type overrides.

5. **Combined router**: Both locale sub-domains share `/locale` prefix to keep
   API surface organized without requiring separate router registrations.
