# BOM Router Decomposition R1: Compare

Date: 2026-04-22

## 1. Goal

Start BOM router decomposition by moving the entire `/compare/*` route family out of the 2146-line `bom_router.py`.

R1 splits 14 public contracts without changing paths, request/response schemas, permissions, status codes, or business logic:

- `GET  /api/v1/bom/compare/schema`
- `GET  /api/v1/bom/compare`
- `GET  /api/v1/bom/compare/delta/preview`
- `GET  /api/v1/bom/compare/delta/export`
- `GET  /api/v1/bom/compare/summarized`
- `GET  /api/v1/bom/compare/summarized/export`
- `POST /api/v1/bom/compare/summarized/snapshots`
- `GET  /api/v1/bom/compare/summarized/snapshots/compare`
- `GET  /api/v1/bom/compare/summarized/snapshots/compare/export`
- `GET  /api/v1/bom/compare/summarized/snapshots/{snapshot_id}/compare/current`
- `GET  /api/v1/bom/compare/summarized/snapshots/{snapshot_id}/compare/current/export`
- `GET  /api/v1/bom/compare/summarized/snapshots/{snapshot_id}/export`
- `GET  /api/v1/bom/compare/summarized/snapshots/{snapshot_id}`
- `GET  /api/v1/bom/compare/summarized/snapshots`

Follows `docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_20260422.md`.

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/bom_compare_router.py` (1106 LOC).
- Moved into the new router:
  - all 8 compare response models (`BOMCompareSummary`, `BOMCompareEntry`, `BOMCompareFieldDiff`, `BOMCompareChangedEntry`, `BOMCompareResponse`, `BOMCompareFieldSpec`, `BOMCompareModeSpec`, `BOMCompareSchemaResponse`)
  - the `SnapshotCreateRequest` request model
  - module-level snapshot store `_BOM_COMPARE_SUMMARIZED_SNAPSHOTS` and its lock
  - compare-only helpers: `_compare_result_to_summarized_rows`, `_rows_to_csv`, `_rows_to_markdown`, `_validate_export_format`, `_find_snapshot`, `_diff_snapshot_rows`, `_diff_to_csv`, `_diff_to_markdown`, `_export_diff`
  - compare-only constants: `_SUMMARIZED_CSV_HEADERS`, `_SUMMARIZED_MD_HEADERS`, `_DIFF_CSV_HEADERS`
  - all 14 compare handlers, preserving source declaration order so that static `/snapshots/compare` routes are declared before dynamic `/snapshots/{snapshot_id}` routes
- Removed the same set from `src/yuantus/meta_engine/web/bom_router.py`; dropped dead imports `io`, `threading`, `uuid`, `timezone`, `StreamingResponse` that only compare handlers used.
- Registered `bom_compare_router` in `src/yuantus/api/app.py` **before** `bom_router` to match the pattern used by `cad_backend_profile_router` in PR #353.

Result: `bom_router.py` went from 2146 → 1063 LOC and now owns 15 endpoints; `bom_compare_router.py` owns 14 endpoints at 1106 LOC.

No public API path, method, request schema, response shape, permission dependency, or tag was intentionally changed.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py` with 6 contracts:
  - module ownership of each moved route,
  - legacy absence of compare routes in `bom_router.py`,
  - registration order (`bom_compare_router` before `bom_router`),
  - exactly one registered route per `(method, path)` pair,
  - `BOM` tag preservation on each moved handler,
  - static `/snapshots/compare` declaration precedes dynamic `/snapshots/{snapshot_id}` so FastAPI does not capture `compare` as a snapshot id.
- Updated existing compare route tests so their `patch(...)` targets resolve against the new module:
  - `test_bom_delta_router.py` — 2 patches repointed.
  - `test_bom_summarized_router.py` — 4 patches repointed.
  - `test_bom_summarized_snapshot_router.py` — 1 patch repointed; `import yuantus.meta_engine.web.bom_router as bom_router_module` changed to `bom_compare_router`.
  - `test_bom_summarized_snapshot_compare_router.py` — 2 patches repointed; `import ... as bom_router_module` changed to `bom_compare_router`.
- Added an autouse `monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")` fixture to the 4 existing compare-route tests above. These tests already overrode `get_current_user` at the router layer but the global auth middleware ran first; the same fixture pattern was landed in PR #340 for `test_locale_router.py` and `test_report_router_permissions.py`. Without this fixture these tests returned `401` on pristine main as well (pre-existing noise, not an R1 regression).
- Added the new contract test to the CI contracts job in `.github/workflows/ci.yml`.

## 4. Verification

Compile:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_compare_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_baseline_enhanced.py \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `110 passed, 1 warning`.

Whitespace:

```bash
git diff --check
```

Result: clean.

Codex review checks:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
# AST source-segment comparison:
# - all moved top-level compare classes/functions are identical to HEAD
#   after replacing @bom_router with @bom_compare_router;
# - all remaining non-compare top-level classes/functions in bom_router.py
#   are unchanged.
PY
```

Result: no differences reported.

Route surface inspection:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
# Enumerated FastAPI routes under /api/v1/bom/compare* and checked:
# - 14 routes are present;
# - each endpoint module is yuantus.meta_engine.web.bom_compare_router;
# - tag list contains "BOM";
# - no duplicate /api/v1/bom route registrations exist.
PY
```

Result: passed.

## 5. Review Checklist

| # | Check | Status |
| --- | --- | --- |
| 1 | All 14 compare endpoints served from `bom_compare_router.py` per contract test | ✅ |
| 2 | `bom_router.py` contains zero `@bom_router.(get|post)` decorators matching `/compare*` | ✅ |
| 3 | `app.py` registers `bom_compare_router` before `bom_router` | ✅ |
| 4 | No change in request / response schema, status code, permission dependency, or tag on any of the 14 endpoints | ✅ |
| 5 | No service-layer code modified (BOMService, comparator, baseline, plugin bom-compare) | ✅ |
| 6 | No migration, no new settings, no new tables | ✅ |
| 7 | Tree / obsolete / children / substitutes / where-used / rollup / convert handlers untouched | ✅ |
| 8 | CI contracts job lists the new `test_bom_compare_router_contracts.py` | ✅ |
| 9 | Static `/snapshots/compare` declared before dynamic `/snapshots/{snapshot_id}` (asserted by contract) | ✅ |
| 10 | Existing compare route tests updated (`patch` target + module alias) | ✅ |
| 11 | Pact provider verifier and CI wiring gate pass | ✅ |

## 6. Explicit Non-Goals Honored

- No split of tree / effective / version / convert / children / obsolete / rollup / where-used / substitutes routes.
- No `BOMCompareService` extraction (routing-only relocation).
- No comparator behavior change (UOM-aware compare from PR #334 / #337 is untouched).
- No plugin `yuantus-bom-compare` surface change.
- No CAD / file / ECO / parallel-tasks / scheduler / shared-dev 142 interaction.

## 7. Pact Provider

R1 is a pure file relocation of public routes; OpenAPI paths remain unchanged. Both the real provider verifier and the CI wiring gate were run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Result: `1 passed, 3 warnings`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py
```

Result: `2 passed`.

## 8. Follow-Up

- R2 candidate (tree / effective / version / convert) is sketched in the taskbook §12 but is a separate bounded increment.
- Pre-existing auth-middleware 401 noise in other router unit tests, if any remain, should be mopped up by the same fixture pattern used here when encountered.
