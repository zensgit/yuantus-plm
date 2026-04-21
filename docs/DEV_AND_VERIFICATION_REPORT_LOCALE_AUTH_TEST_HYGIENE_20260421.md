# DEV / Verification - Report Locale Auth Test Hygiene - 2026-04-21

## 1. Goal

Remove local-only router test noise where locale and report permission unit tests returned `401 Missing bearer token` before reaching the mocked router dependencies.

This is test hygiene only. Production authentication behavior is unchanged.

## 2. Root Cause

The affected tests construct `TestClient(create_app())` and mock route dependencies directly.

On local machines with `AUTH_MODE=required`, `AuthEnforcementMiddleware` runs before FastAPI route dependency overrides. Without a bearer token, the middleware returns `401`, so tests never reach:

- `locale_router` mocked services,
- `report_router` mocked `get_current_user`,
- report permission assertions.

## 3. Delivered

Updated tests:

- `src/yuantus/meta_engine/tests/test_locale_router.py`
- `src/yuantus/meta_engine/tests/test_report_router_permissions.py`

Change:

- added per-file autouse fixtures that set `get_settings().AUTH_MODE` to `optional` via `monkeypatch`;
- retained existing `get_db` and `get_current_user` dependency overrides;
- did not change production router, middleware, settings, or auth dependency code.

## 4. Verification

Focused verification:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py -vv
```

Observed:

```text
10 passed
```

Adjacent regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_locale_router.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py \
  src/yuantus/meta_engine/tests/test_locale_service.py \
  src/yuantus/meta_engine/tests/test_report_locale_service.py \
  src/yuantus/meta_engine/tests/test_reports_advanced_search.py \
  src/yuantus/meta_engine/tests/test_report_service_bom_uom.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed:

```text
58 passed
```

## 5. Acceptance Criteria

| Criterion | Status |
| --- | --- |
| 6 locale router tests no longer fail with local `AUTH_MODE=required` | Pass |
| 4 report router permission tests no longer fail with local `AUTH_MODE=required` | Pass |
| No production auth code changed | Pass |
| Existing route dependency overrides remain in place | Pass |

## 6. Boundary

- No runtime auth behavior changes.
- No new public endpoints.
- No token fixture or identity DB seeding added.
- No attempt to loosen production `AUTH_MODE=required`.
