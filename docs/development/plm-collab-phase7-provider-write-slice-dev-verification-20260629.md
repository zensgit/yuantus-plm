# PLM × MetaSheet — Phase 7 Provider Write-Slice Dev & Verification (2026-06-29)

Type: dev & verification record for the **#901-ratified** Phase 7 governed BOM multi-table
write-back **provider endpoint** (PR #904). Companion to the broker-unblock + Slice-0 closeout
(2026-06-28). The provider build is the work; the downstream consumer amendment is owner-gated.

## 1. What was built (PR #904)

The ratified Day-2 model (#901, **supersedes #896's create-pending-ECO draft**): a **synchronous,
lifecycle-guarded, in-place apply** satisfying consumer contract metasheet2 **#3332**.

`PATCH /api/v1/bom/multitable/{part_id}/lines/{bom_line_id}` + an `Idempotency-Key` header →
`200 {ok, bom_line_id}`. Guard order (write-precedent 403s, fail-closed before lookups):
`is_entitled("bom_multitable_writeback")` 403 → `"Part BOM"`/update 403 → empty | missing-key 400
→ part-missing | line-not-a-direct-`"Part BOM"`-child 404 → `is_item_locked`→409 → atomic apply.

Atomic apply = one transaction: mutate the cell in place **and** insert a `meta_bom_writeback_audit`
row (UNIQUE `idempotency_key` = single-use replay guard **and** before/after audit). A replayed key
→ rollback (no double-apply) → cached `200` (same line+payload) or `409` (different line/payload);
any failure rolls **both** back (no partial state, #901 §3). The ECO change-control route is deferred.

| Piece | File |
|---|---|
| Endpoint + guards + atomic apply | `meta_engine/web/bom_multitable_router.py` |
| Write SKU `bom_multitable_writeback → plm.bom_multitable_writeback` | `app_framework/entitlement_service.py` |
| Audit + replay model (+ bootstrap registration) | `models/bom_writeback_audit.py`, `bootstrap.py` |
| Migration (default tree) | `migrations/versions/p7_bom_writeback_001_*.py` |
| Tenant baseline (regenerated; single-file invariant kept) | `migrations_tenant/versions/t1_initial_tenant_baseline.py` |
| Pact sync + writable fixture + write-license seed | `contracts/pacts/metasheet2-yuantus-plm.json`, `api/tests/test_pact_provider_yuantus_plm.py` |
| Unit tests | `meta_engine/tests/test_bom_multitable_writeback.py` |
| Route-pin 727→728 (4 sites + router 2→3); ci.yml; #896 doc | (route-count tests, `ci.yml`, `…phase7-writeback-contract-draft-20260627.md`) |

## 2. Verification (local, py3.11)

- **Writeback unit 13/13:** unentitled-403, unpermitted-403, missing-key-400, empty-400,
  part-404, line-not-direct-child-404, **lifecycle-locked-409 (real `LifecycleState`, per #901 §5)**,
  unlocked-200, in-place-apply + before/after audit + **no `eco_id`**, replay cached-200 (no
  double-apply), replay-different-payload-409, replay-different-line-409, commit-failure-rollback.
- **Strict pact verifier green** — the synced PATCH interaction (entitled + writable `R8`-under-`P4`)
  is collected and returns 200; the full verifier + the anti-defang meta-gate stay green.
- **Regressions green:** route-pins (728), read projection (router 2→3), entitlement key-set,
  tenant-baseline drift/determinism/single-file/no-global-FK.
- **Migrations:** `alembic upgrade head` OK on `migrations/` + identity; tenant baseline regenerated
  via `scripts/generate_tenant_baseline.py` (diff = only the new table).

## 3. #901 lineage (how this reconciled mid-build)

#896 (Slice-0, this session) drafted a **create-pending-ECO intent**. During the build, **#901**
landed on main — owner-**ratified** the **opposite** (synchronous in-place apply; ECO deferred) and
named #896 superseded. The build was confirmed with the owner and rewritten to #901; #896's doc 口径
is corrected in lockstep so no future session re-derives the ECO seam.

## 4. CI / downstream (NOT in this PR)

- The broker `can-i-deploy` step verifies against the **live broker**; it should pass because the
  consumer `main` pact is still **33 interactions / 0 write-back** (provider leads, #901 §9).
- **Owner-gated metasheet2 follow-up (separate slice):** `PLMAdapter.updateBomMultitableLine` sends
  `Idempotency-Key`; providerState text → `plm.bom_multitable_writeback`; **re-add** the amended
  interaction to the broker (reverting #3337) **after this lands**. Until then the consumer is
  intentionally contract-ahead.

## References
- Ratified design — `docs/development/plm-collaboration-phase7-writeback-day2-design-resolution-20260629.md` (#901)
- Day-1 taskbook — `…phase7-writeback-provider-endpoint-taskbook-20260628.md` (#899)
- Slice-0 (superseded) — `…phase7-writeback-contract-draft-20260627.md` (#896)
- Consumer contract — metasheet2 #3332
