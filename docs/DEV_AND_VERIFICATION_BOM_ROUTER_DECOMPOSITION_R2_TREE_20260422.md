# BOM Router Decomposition R2: Tree / Effective / Version / Convert

Date: 2026-04-22 (executed 2026-04-23)

## 1. Goal

Execute R2 of the BOM router decomposition per the merged taskbook
`docs/DEVELOPMENT_CLAUDE_TASK_BOM_ROUTER_DECOMPOSITION_R2_20260422.md` (merged on main
at `f48fed5`). Move the 5 "BOM structure read + EBOM→MBOM conversion" endpoints out of
`bom_router.py` (post-R1: 1062 LOC, 15 endpoints) into a new `bom_tree_router.py`
without changing paths, request/response schemas, permissions, status codes, or
business logic:

- `GET  /api/v1/bom/{item_id}/effective`
- `GET  /api/v1/bom/version/{version_id}`
- `POST /api/v1/bom/convert/ebom-to-mbom`
- `GET  /api/v1/bom/{parent_id}/tree`
- `GET  /api/v1/bom/mbom/{parent_id}/tree`

Follows the R1 compare-split precedent
(`docs/DEV_AND_VERIFICATION_BOM_ROUTER_DECOMPOSITION_R1_COMPARE_20260422.md`).

## 2. Runtime Changes

- Added `src/yuantus/meta_engine/web/bom_tree_router.py` (302 LOC).
- Moved into the new router:
  - the `_parse_config_selection` helper (only callers are the 3 R2 handlers that
    accept a `config` query param — confirmed by pre-move `rg` on current main),
  - the R2-only request/response DTOs `ConvertBomRequest` and `ConvertBomResponse`,
  - the `BOMConversionService` import (only the convert handler uses it),
  - all 5 R2 handlers, preserving source declaration order
    (`effective` → `version` → `convert` → `tree` → `mbom tree`).
- Removed the same set from `src/yuantus/meta_engine/web/bom_router.py`; also
  dropped the now-dead `import json` (only `_parse_config_selection` used it).
- Registered `bom_tree_router` in `src/yuantus/api/app.py` **between**
  `bom_compare_router` and `bom_router`, producing the canonical 3-way BOM
  registration order: `bom_compare_router` → `bom_tree_router` → `bom_router`.

Result: `bom_router.py` went from 1062 → 793 LOC and now owns 10 endpoints
(children POST / DELETE, obsolete scan, obsolete resolve, weight rollup,
substitutes CRUD, where-used). `bom_tree_router.py` owns 5 endpoints at 302 LOC.

No public API path, method, request schema, response shape, permission dependency,
tag, HTTP status code, or rollback/service-call behavior was intentionally
changed. `BOMService`, `BOMConversionService`, `BOMObsoleteService`,
`BOMRollupService`, `SubstituteService` internals are unchanged.

## 3. Test Changes

- Added `src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py`
  (6 route-ownership contracts):
  - module ownership of each of the 5 moved routes,
  - legacy absence of tree/effective/version/convert routes in `bom_router.py`,
  - 3-way registration order in `app.py`
    (`bom_compare_router` → `bom_tree_router` → `bom_router`),
  - exactly one registered route per `(method, path)` pair,
  - `BOM` tag preservation on each moved handler,
  - source declaration order
    `effective` → `version` → `convert` → `tree` → `mbom tree`
    (documented as a **mechanical relocation guard**, not a static-vs-dynamic
    path-collision fix — unlike R1's `/snapshots/compare` vs
    `/snapshots/{snapshot_id}` case, the 5 R2 paths do not currently collide
    by shape).
- Added `src/yuantus/meta_engine/tests/test_bom_tree_router.py`
  (14 direct route behavior tests required by taskbook §4.5 — no such file
  existed on pristine main pre-R2):
  - effective: item-not-found 404, permission-denied 403, full parameter
    forwarding (date, levels, lot/serial/unit, config JSON) into
    `BOMService.get_bom_structure`,
  - version: happy-path `BOMService.get_bom_for_version` call, ValueError→404,
  - convert: root-not-found 404, non-Part root 400, permission-denied 403 on
    the second of the two permission checks (`Part BOM` add), success path
    returning MBOM identifiers, ValueError rollback-and-400 behavior,
  - tree: full parameter forwarding (depth, effective_date, lot/serial/unit,
    config JSON, no `relationship_types`), invalid config JSON → 400,
  - mbom tree: rejection of non-`Manufacturing Part` 400, correct
    `relationship_types=["Manufacturing BOM"]` forwarding.

  Uses the **isolated-router test pattern** (`FastAPI(); include_router(...)`)
  so the global `AuthEnforcementMiddleware` is not in the stack — no
  `AUTH_MODE=optional` autouse fixture is required in this file. This matches
  the existing `test_bom_obsolete_rollup_router.py` pattern; no pre-existing
  R2 test files needed patch-target updates because none of them referenced
  R2 handler symbols (`get_effective_bom`, `get_bom_by_version`,
  `convert_ebom_to_mbom`, `get_bom_tree`, `get_mbom_tree`,
  `_parse_config_selection`, `ConvertBomRequest`, `ConvertBomResponse`, or
  `BOMConversionService` via `yuantus.meta_engine.web.bom_router`).
- Added `test_bom_tree_router_contracts.py` to the contracts job in
  `.github/workflows/ci.yml`, alphabetically immediately after
  `test_bom_compare_router_contracts.py` (R1's entry).

## 4. Pre-Move Guards Honored

Per taskbook §4.6 / §9, the implementation re-ran the pre-move guard on current
`main` before deleting the helper:

```bash
rg -n "_parse_config_selection" src/yuantus/meta_engine/web/bom_router.py
```

Result on post-R1 `main` (`f48fed5`):

```
31:def _parse_config_selection(config: Optional[str]) -> Optional[Dict[str, Any]]:
210:    config_selection = _parse_config_selection(config)
351:    config_selection = _parse_config_selection(config)
400:    config_selection = _parse_config_selection(config)
```

All 3 callers (L210 effective, L351 tree, L400 mbom tree) are inside the R2 set.
No non-R2 caller exists, so the helper can migrate together with the 5 handlers.

Additional post-move sanity checks (from the advisor):

```bash
grep -cE "^@bom_router\." src/yuantus/meta_engine/web/bom_router.py           # -> 10 (was 15)
grep -cE "^@bom_tree_router\." src/yuantus/meta_engine/web/bom_tree_router.py # -> 5
```

And the presence grep for any residue in the legacy module:

```bash
grep -n "_parse_config_selection\|BOMConversionService\|^import json$\|\
ConvertBomRequest\|ConvertBomResponse" \
  src/yuantus/meta_engine/web/bom_router.py
```

Result: no matches.

## 5. Verification

Compile:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/bom_router.py \
  src/yuantus/meta_engine/web/bom_tree_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Focused regression (includes all BOM-adjacent unit test files that could be
affected by the move, plus the doc-index contracts, plus both new R2 tests):

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_tree_router.py \
  src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py \
  src/yuantus/meta_engine/tests/test_bom_delta_preview.py \
  src/yuantus/meta_engine/tests/test_bom_delta_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py \
  src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py \
  src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_baseline_enhanced.py \
  src/yuantus/meta_engine/tests/test_bom_rollup_service.py \
  src/yuantus/meta_engine/tests/test_bom_uom_aware_duplicate_guard.py \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `143 passed, 1 warning`.

Pact provider verifier (§4.8 requires running the real provider, not just the
wiring gate, because R2 moves public OpenAPI routes):

```bash
.venv/bin/python -m pytest -q src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py
```

Results:

- Pact provider verifier: `1 passed, 3 warnings`.
- CI wiring gate: `2 passed`.

Whitespace:

```bash
git diff --check
```

Result: clean.

Codex review checks:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
# AST source-segment comparison:
# - all moved top-level R2 classes/functions are identical to HEAD
#   after replacing @bom_router with @bom_tree_router;
# - all remaining non-R2 top-level classes/functions in bom_router.py
#   are unchanged.
PY
```

Result: no differences reported.

Route surface inspection:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
# Enumerated FastAPI routes for the 5 R2 paths and checked:
# - all 5 are present;
# - each endpoint module is yuantus.meta_engine.web.bom_tree_router;
# - tag list contains "BOM".
PY
```

Result: passed.

## 6. Review Checklist

| # | Check | Status |
| --- | --- | --- |
| 1  | All 5 R2 endpoints served from `bom_tree_router.py` per contract test | ✅ |
| 2  | `bom_router.py` contains zero `@bom_router.(get|post)` decorators matching the 5 R2 paths | ✅ |
| 3  | `app.py` registers `bom_compare_router` → `bom_tree_router` → `bom_router` (asserted) | ✅ |
| 4  | No change in request / response schema, status code, permission dependency, or tag on any of the 5 endpoints | ✅ |
| 5  | No service-layer code modified (`BOMService`, `BOMConversionService`, baseline, obsolete, rollup, substitute) | ✅ |
| 6  | No migration, no new settings, no new tables | ✅ |
| 7  | R1 compare seal preserved: `bom_compare_router.py` and every compare test untouched | ✅ |
| 8  | Children / obsolete / rollup / where-used / substitutes handlers untouched | ✅ |
| 9  | CI contracts job lists the new `test_bom_tree_router_contracts.py` | ✅ |
| 10 | Source declaration order `effective` → `version` → `convert` → `tree` → `mbom tree` (asserted) | ✅ |
| 11 | `_parse_config_selection` pre-move guard re-run; only R2 callers found | ✅ |
| 12 | `test_bom_tree_router.py` covers all 5 endpoints at behavior level per §4.5 | ✅ |
| 13 | Pact provider verifier and CI wiring gate pass | ✅ |

## 7. Explicit Non-Goals Honored

- No split of children / obsolete / rollup / where-used / substitutes routes
  (R3+ candidates; deferred per taskbook §12).
- No `BOMConversionService` / `BOMService` internals extraction (routing-only
  relocation).
- No comparator or plugin `yuantus-bom-compare` surface change.
- No CAD / file / ECO / parallel-tasks / scheduler / shared-dev 142 interaction.
- No modification to `bom_compare_router.py` or any compare test (R1 seal).

## 8. Pact Provider

R2 is a pure file relocation of public routes; OpenAPI paths remain unchanged.
Both the real provider verifier and the CI wiring gate were run (see §9).

## 9. Execution Record

Commands actually run during this PR (against `feat/bom-tree-router-r2-20260422`
off `f48fed5`):

- `.venv/bin/python -m py_compile src/yuantus/meta_engine/web/bom_router.py src/yuantus/meta_engine/web/bom_tree_router.py src/yuantus/api/app.py` — passed.
- `.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py` — `6 passed`.
- `.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_bom_tree_router.py` — `14 passed`.
- Full focused regression (§5) — `143 passed, 1 warning`.
- Pact provider verifier — `1 passed, 3 warnings`.
- CI Pact wiring gate — `2 passed`.
- `git diff --check` — clean.

## 10. Follow-Up

- R3 candidate (`children` CRUD, 2 endpoints) is the natural next bounded
  increment as sketched in the R2 taskbook §12, but **only after** this cycle's
  non-technical review points (backlog triage, external signal collection,
  scheduler decision gate per the next-cycle plan) have been re-assessed.
- If any new test files whose `patch(...)` targets reference R2 symbols
  (`get_effective_bom`, `get_bom_by_version`, `convert_ebom_to_mbom`,
  `get_bom_tree`, `get_mbom_tree`, `_parse_config_selection`,
  `ConvertBomRequest`, `ConvertBomResponse`, `BOMConversionService`) land
  between this PR and a hypothetical R2 revert, they must be repointed at
  `bom_tree_router`, not `bom_router`.
- No bounded increment should combine R3 with any other BOM slice or unrelated
  file move.
