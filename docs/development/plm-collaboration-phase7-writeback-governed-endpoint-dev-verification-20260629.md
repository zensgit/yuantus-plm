# Phase-7 BOM multi-table write-back — governed endpoint (development & verification) — 2026-06-29

Implements the owner-ratified Day-2 design resolution (#901) + its G1-G5 build conformance
gates. Built on a fresh `origin/main` worktree @ `6a91a22f` (which already carries #903's
gates). Provider-side only; the route is gated default-off behind the write entitlement.

## What shipped

- **Endpoint** `PATCH /api/v1/bom/multitable/{part_id}/lines/{bom_line_id}` -> `200 {ok, bom_line_id}`
  (`web/bom_multitable_router.py`). The Draft/editable-state fast path of #3332 — NOT auto-ECO.
- **Governed service** `services/bom_multitable_writeback_service.py` — whitelist + null-clear
  canonicalisation, lifecycle guard, provider-side single-use idempotency/replay, atomic audit.
- **Model + dual migration** `meta_bom_writeback_audit` (`models/bom_writeback_audit.py`):
  global `migrations/versions/bom_wb_audit_001_*` (chained on head `txn_history_001`) + the
  tenant tree via the deterministic `t1_initial_tenant_baseline` regeneration (`--check` clean).
- **Write entitlement** `FEATURE_APP_NAMES["bom_multitable_writeback"] = {"plm.bom_multitable_writeback"}`
  + `WRITE_FEATURE_KEY` in the write module + the pact write-license fixture seed.

## G1-G5 conformance (how each gate is met)

- **G1 guard order** — `is_entitled(WRITE_FEATURE_KEY)` 403 -> `check_permission("Part BOM",
  update)` 403 -> 400 (Idempotency-Key / body) -> 404 (line in part) -> 409 (parent lifecycle).
  The route reads the `Idempotency-Key` header and body MANUALLY via `Request` *after* the 403
  gates, so FastAPI cannot 422 ahead of the gate. Pinned by a test: unentitled + missing-part +
  bad body -> **403, not 404/400/422**.
- **G2 same-PR registration** — the write key is registered in `FEATURE_APP_NAMES` in the same
  change (else `is_entitled` raises -> 500); `WRITE_FEATURE_KEY` lives in the write module, not
  the read projection service; the pact fixture seeds the write license.
- **G3 idempotency before mutation** — the combined `meta_bom_writeback_audit` row (UNIQUE
  `idempotency_key`) is inserted FIRST inside `begin_nested()`; an `IntegrityError` short-circuits
  BEFORE any mutation. Same key + same canonical payload -> cached 200 with NO re-apply; same
  key + DIFFERENT payload -> 409 (compared on `request_hash` of the canonical patch, not raw
  JSON). `before` is snapshotted before the reassignment; an audit/mutation failure rolls back
  atomically.
- **P1 properties** — applied via copy-on-write whole-dict reassign (`merged = dict(...);
  line.properties = merged`), never in-place `.update()`. A DB-reload test asserts the mutation
  actually persisted; a replay test asserts a duplicate key does NOT re-write.
- **G5 lifecycle 409** — the pact fixture is inert on lifecycle (Part has no `lifecycle_map_id`,
  `state` is a bare string), so the 409 is proven by a PROVIDER test with a real
  `LifecycleState(version_lock=True)` parent -> 409, plus a Draft parent -> 200.

## Verification

`.venv-wp13` (Python 3.11.15), worktree src on `PYTHONPATH`.

- `test_bom_multitable_writeback.py` — **14 passed**. Covers: unentitled-is-403-not-404/400/422;
  permission 403; missing/blank/>64 Idempotency-Key 400; malformed body 400; unknown-only body
  (empty whitelist) 400; line-not-in-part 404; locked-parent 409 (real LifecycleState) + Draft
  200 with DB-reload; replay caches 200 with no double-write; same-key-different-payload 409;
  audit before/after captured; mutation-failure rolls back audit atomically.
- `test_entitlement_service.py` + the new file together — **34 passed** (no regression).
- `generate_tenant_baseline.py --check` — `ok: committed revision matches generator output`.
- `py_compile` clean on all new/edited modules.

## Pact status (honest scope)

The provider is implemented and verifier-ready: the write-license fixture is seeded so the PATCH
success interaction would verify `entitled:true` -> 200. **The broker/consumer loop is NOT
closed in this PR** — adding the amended PATCH interaction (with the `Idempotency-Key` header)
and re-adding it to the broker is the metasheet2 **#3332** consumer follow-up (it must actually
send the header; a providerState text rename alone would hit the section-1 400). Reverting
#3337's broker removal happens once #3332 lands.

## Out of scope / deferred (per #901)

ECO route for Released/locked BOMs (the 409 path); `If-Match`/412 optimistic concurrency (v1 is
last-write-wins, bounded by the single-use guard + lifecycle lock); value-transforming retype;
any FE; bulk/multi-line writes.

## Sequence remaining

This lands after the `contracts` gate -> then metasheet2 #3332 (providerState text +
`Idempotency-Key`) -> broker re-add of the amended interaction.
