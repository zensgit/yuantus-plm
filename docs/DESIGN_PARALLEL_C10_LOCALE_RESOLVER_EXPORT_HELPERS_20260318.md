# C10 – Locale Description Resolver and Export Helpers

**Branch**: `feature/claude-c10-locale-resolver`
**Date**: 2026-03-18
**Status**: Implemented & Verified

---

## 1. Objective

Extend the C6 locale baseline with:
- A translation resolve endpoint that applies a fallback language chain
- A fallback preview endpoint showing the full resolution chain
- An export context helper that other domains (BOM, ECO, quality) can consume
  to get locale-aware formatting settings in a single call

## 2. New Service Methods

### 2.1 LocaleService (3 new methods)

| Method | Description |
|---|---|
| `resolve_translation(...)` | Resolve single field with fallback chain; returns value, resolved lang, chain |
| `resolve_translations_batch(...)` | Resolve multiple fields for one record; returns resolved/missing/fallbacks_used |
| `fallback_preview(...)` | Show full resolution chain for a single field |

### 2.2 ReportLocaleService (1 new method)

| Method | Description |
|---|---|
| `get_export_context(lang, report_type?)` | Build flat dict with all formatting settings for export pipelines |

## 3. New Endpoints (3)

| Method | Path | Description |
|---|---|---|
| POST | `/locale/translations/resolve` | Batch resolve fields with fallback chain |
| GET | `/locale/translations/fallback-preview` | Show resolution chain for one field |
| GET | `/locale/export-context` | Get locale formatting context for exports |

## 4. Resolve Contract

### POST /locale/translations/resolve

Request:
```json
{
  "record_type": "item",
  "record_id": "itm-1",
  "fields": ["name", "description"],
  "lang": "zh_CN",
  "fallback_langs": ["en_US"]
}
```

Response:
```json
{
  "resolved": [
    {"field": "name", "lang": "zh_CN", "value": "螺栓"},
    {"field": "description", "lang": "en_US", "value": "Hex Bolt M10"}
  ],
  "missing": [],
  "fallbacks_used": ["en_US"]
}
```

### GET /locale/translations/fallback-preview

Response:
```json
{
  "request": {
    "record_type": "item",
    "record_id": "itm-1",
    "field_name": "name",
    "primary_lang": "zh_CN",
    "fallback_chain": ["en_US"]
  },
  "resolution_chain": [
    {"lang": "zh_CN", "exists": false, "value": null, "source_value": null, "state": null},
    {"lang": "en_US", "exists": true, "value": "Bolt", "source_value": null, "state": "draft"}
  ],
  "resolved_value": "Bolt",
  "resolved_from_lang": "en_US"
}
```

### GET /locale/export-context

Response:
```json
{
  "resolved": true,
  "lang": "zh_CN",
  "report_type": "bom_export",
  "profile_id": "...",
  "profile_name": "BOM ZH",
  "number_format": "#,##0.00",
  "date_format": "YYYY年MM月DD日",
  "time_format": "HH:mm:ss",
  "timezone": "Asia/Shanghai",
  "paper_size": "a4",
  "orientation": "portrait",
  "header_text": null,
  "footer_text": null,
  "logo_path": null,
  "fallback_lang": null
}
```

## 5. Design Decisions

1. **Fallback chain is caller-supplied**: The resolve endpoints accept an explicit
   `fallback_langs` list rather than inferring from `fallback_lang` on the
   profile. This gives callers full control over resolution order.

2. **Export context returns defaults when no profile matches**: Instead of 404,
   `get_export_context` returns `resolved: false` with safe defaults so callers
   don't need special error handling.

3. **No new models or tables**: All C10 features build on the existing
   Translation and ReportLocaleProfile models from C6.
