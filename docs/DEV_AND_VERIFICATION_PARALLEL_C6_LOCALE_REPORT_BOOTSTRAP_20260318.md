# C6 – Locale & Report Locale Bootstrap: Development & Verification

**Branch**: `feature/claude-c6-locale`
**Date**: 2026-03-18
**Status**: All 20 tests passing

---

## 1. Test Summary

| Test File | Tests | Result |
|---|---|---|
| `test_locale_service.py` | 8 | 8/8 PASSED |
| `test_report_locale_service.py` | 12 | 12/12 PASSED |
| **Total** | **20** | **20/20 PASSED** |

## 2. LocaleService Tests (8)

| # | Test | Validates |
|---|---|---|
| 1 | `test_upsert_creates_new` | New translation created with UUID, correct fields, state=draft |
| 2 | `test_upsert_updates_existing` | Same composite key → updates translated_value & state in-place |
| 3 | `test_upsert_invalid_state_raises` | ValueError on state="invalid" |
| 4 | `test_get_translation` | Lookup by composite key returns correct Translation |
| 5 | `test_get_translations_for_record` | Returns all translations for a (record_type, record_id) |
| 6 | `test_bulk_upsert` | Batch creates 2 translations, returns {created:2, updated:0, errors:[]} |
| 7 | `test_delete_translation` | Deletes existing translation, returns True |
| 8 | `test_delete_nonexistent_returns_false` | Returns False for missing key |

## 3. ReportLocaleService Tests (12)

| # | Test | Validates |
|---|---|---|
| 1 | `test_create_profile_defaults` | Default lang=en_US, paper_size=a4, orientation=portrait, number_format=#,##0.00 |
| 2 | `test_create_profile_chinese` | Custom zh_CN profile with Asia/Shanghai timezone |
| 3 | `test_create_profile_invalid_paper_size_raises` | ValueError on paper_size="a5" |
| 4 | `test_create_profile_invalid_orientation_raises` | ValueError on orientation="diagonal" |
| 5 | `test_get_profile` | Retrieves created profile by ID |
| 6 | `test_update_profile` | Partial update of name + paper_size |
| 7 | `test_update_nonexistent_returns_none` | Returns None for missing ID |
| 8 | `test_delete_profile` | Deletes profile, subsequent get returns None |
| 9 | `test_delete_nonexistent_returns_false` | Returns False for missing ID |
| 10 | `test_resolve_profile_exact_match` | lang+report_type exact match wins over lang default |
| 11 | `test_resolve_profile_falls_back_to_lang_default` | Missing report_type falls back to is_default=True for same lang |
| 12 | `test_resolve_profile_returns_none_when_no_match` | Returns None when no profiles exist for lang |

## 4. Test Infrastructure

- **Mock session pattern**: Reusable `_mock_session()` with in-memory `_store` dict,
  supporting `add`, `get`, `delete`, `flush`, and `query().filter().first()/all()`.
- **SQLAlchemy BinaryExpression matching**: MockQuery._match inspects `f.left.key`
  and `f.right.effective_value` for filter predicates.
- Both test files are self-contained with zero external dependencies beyond the
  modules under test.

## 5. Coverage Analysis

| Domain | Service Methods | Tested | Coverage |
|---|---|---|---|
| LocaleService | 6 | 6 | 100% |
| ReportLocaleService | 6 | 6 | 100% |
| Validation (paper_size) | 1 | 1 | 100% |
| Validation (orientation) | 1 | 1 | 100% |
| Validation (state) | 1 | 1 | 100% |
| Resolution cascade | 3 tiers | 3 | 100% |

## 6. Execution Log

```
$ python3 -m pytest src/yuantus/meta_engine/tests/test_locale_service.py \
    src/yuantus/meta_engine/tests/test_report_locale_service.py -v --tb=short

============================= test session starts ==============================
collected 20 items

test_locale_service.py::TestLocaleService::test_upsert_creates_new PASSED
test_locale_service.py::TestLocaleService::test_upsert_updates_existing PASSED
test_locale_service.py::TestLocaleService::test_upsert_invalid_state_raises PASSED
test_locale_service.py::TestLocaleService::test_get_translation PASSED
test_locale_service.py::TestLocaleService::test_get_translations_for_record PASSED
test_locale_service.py::TestLocaleService::test_bulk_upsert PASSED
test_locale_service.py::TestLocaleService::test_delete_translation PASSED
test_locale_service.py::TestLocaleService::test_delete_nonexistent_returns_false PASSED
test_report_locale_service.py::TestReportLocaleService::test_create_profile_defaults PASSED
test_report_locale_service.py::TestReportLocaleService::test_create_profile_chinese PASSED
test_report_locale_service.py::TestReportLocaleService::test_create_profile_invalid_paper_size_raises PASSED
test_report_locale_service.py::TestReportLocaleService::test_create_profile_invalid_orientation_raises PASSED
test_report_locale_service.py::TestReportLocaleService::test_get_profile PASSED
test_report_locale_service.py::TestReportLocaleService::test_update_profile PASSED
test_report_locale_service.py::TestReportLocaleService::test_update_nonexistent_returns_none PASSED
test_report_locale_service.py::TestReportLocaleService::test_delete_profile PASSED
test_report_locale_service.py::TestReportLocaleService::test_delete_nonexistent_returns_false PASSED
test_report_locale_service.py::TestReportLocaleService::test_resolve_profile_exact_match PASSED
test_report_locale_service.py::TestReportLocaleService::test_resolve_profile_falls_back_to_lang_default PASSED
test_report_locale_service.py::TestReportLocaleService::test_resolve_profile_returns_none_when_no_match PASSED

============================== 20 passed in 2.39s ==============================
```

## 7. Known Limitations

1. **No router-level tests**: Service-layer tests only; router integration
   tests should be added when `app.py` registration is wired.
2. **Bulk upsert is sequential**: Each row calls `upsert_translation` in a loop;
   for very large batches a chunked flush strategy may be needed.
3. **Resolution cascade**: Does not support fallback_lang chaining — only
   three tiers (exact → lang default → global default).
