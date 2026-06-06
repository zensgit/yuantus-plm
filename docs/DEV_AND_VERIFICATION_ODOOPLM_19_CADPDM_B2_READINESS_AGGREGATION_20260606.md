# DEV & Verification: OdooPLM 19 CAD-PDM B2 readiness aggregation

Date: 2026-06-06

Folds the B2 assembly-release diagnostics (`item_release`, #731) into the
`release_readiness` surface so a blocking or missing direct `ASSEMBLY` child is
**visible before promote**, not only as a last-second hard stop. Advisory only —
the B2 hard gate is unchanged. Thin slice: one aggregation block + one helper, **no
new route**.

## Scope (this PR)

- `release_readiness_service.get_item_release_readiness()` — append an
  `item_release` resource (uniform `kind`/`resource_type`/`resource_id`/`name`/
  `state`/`errors`/`warnings` shape, exactly like `mbom`/`routing`/`baseline`).
- `ItemReleaseService.has_assembly_edges(item_id)` — small public presence query
  (the D1 gate; the edge concept belongs to `ItemReleaseService`, not the readiness
  service).
- New **service-level** test `test_release_readiness_item_release.py` (the router
  contract test mocks the service, so it cannot cover the real aggregation).

## As built (against the locked decisions)

- **D1 — include only when there are ASSEMBLY edges** — the `item_release` resource
  appears **iff** the item has ≥1 current direct `ASSEMBLY` edge (child present OR
  dangling). A leaf part has nothing to show and is skipped (matches the existing
  "list resources that exist"口径; keeps `summary` free of noise resources). This
  needs an edge-presence signal that `errors` alone cannot give — an assembly whose
  children are **all released** has 0 errors but must still surface as
  `item_release: ok`. Hence `has_assembly_edges` (a presence query, no child
  resolution), not a check on the error list.
- **D2 — ruleset passthrough** — the endpoint's `ruleset_id` (default `"readiness"`)
  flows straight through, exactly as for the sibling kinds. `item_release` supports
  `{default, readiness}`; `readiness` drops `item.not_already_released`, so only the
  child/dangling findings show. No hard-coding; no new failure mode (same common
  ruleset set as `mbom`/`baseline`; the router already maps `ValueError` → 400).
- **D4 — resource label** — `name` = `get_item_number(item.properties)` (an Item has
  no top-level `name`; the number is the readable label), `state` = `item.state`;
  `None` when the item can't be loaded.
- **Fail-closed carries through** — a dangling edge surfaces as `child_missing`
  (the #731 fix) in the readiness errors, so a broken BOM reference is visible here
  too, not just at promote.
- **No route, no gate change** — aggregation lives in the service body; the router
  is untouched. **Route-count stays 705** (no pin bump). `summary.by_kind` is a
  dynamic rollup → the new kind is included automatically (no enum to edit).

## Not in this PR (non-goals)

- No change to the B2 hard gate (`LifecycleService.promote`) or its `item_release`
  rulesets.
- No new route / no router signature change; no frontend.
- B1 (Superseded / status semantics) remains taskbook-first, separate.

## Verification (Python 3.11 venv, requirements.lock)

- `pytest test_release_readiness_item_release.py` → **4 passed**: unreleased direct
  child → `item_release` resource with `errors[0].rule_id == bom.children_all_released`
  + `summary.by_kind` counts; dangling edge → `errors[0].code == child_missing`;
  all-released assembly → resource present, **0 errors**, `ok_resources == 1` (the
  `has_assembly_edges` case); leaf → **no** `item_release` resource and absent from
  `by_kind`.
- B2 gate `test_item_release_gate.py` → **12 passed** (the `has_assembly_edges`
  addition breaks nothing).
- Test dual-registered (`ci.yml` contracts list, sorted between
  `test_readme_runbooks_sorting_contracts` and `test_report_dashboard_router_contracts`)
  + `conftest.py` no-DB allowlist; **hermetic** (clears lru-cached `get_settings()`).
- Full CI contracts list → green; `create_app()` unchanged at **705 routes**.
- `test_release_readiness_router.py` (mocked-service router test) is unaffected by
  the service change — its local failures are the pre-existing **401** auth noise
  (fails identically on clean main; the router test is not in the CI contracts list).
- `git diff --check` clean.
