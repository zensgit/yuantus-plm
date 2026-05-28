# Development Plan: PLM→ERP Publication Contract

Date: 2026-05-27

Type: **Program-level plan / scope MD (doc-only).** Converts the OdooPLM
comparison's **G2** gap — *PLM→ERP downstream surface* — into an executable
program. It defines the program shape and the contracts the R1-A taskbook must
lock; it does **not** write implementation and is **not** the R1-A taskbook.
Each subsequent slice (R1-A taskbook, R1-B API, R2 adapter) needs its own
explicit opt-in.

Origin: `DEVELOPMENT_ODOOPLM_GROUNDED_COMPARISON_20260525.md` (#643) §5 G2 + §6.2.
The comparison's #1 gap (G1 CAD last-mile) is now closed on the software side
(`DEV_AND_VERIFICATION_CAD_HELPER_BRIDGE_LAST_MILE_CLOSEOUT_20260527.md`, #662);
G2 is the next main line.

## 1. Goal & framing

Build the contract for **"PLM released data → an external ERP"** — an
**outbound publication contract**, not an ERP implementation and not an
Odoo-specific integration. Yuantus exposes *what is publishable and why*; an
external ERP adapter (a later track) consumes it. Per the comparison §6.2: extend
the existing `latest_released_guard` / `suspended_guard` semantics to the ERP
publication surface; **do not build an ERP, do not bind to Odoo**.

## 2. Scope

- R1 delivers an **adapter-neutral** "publication-readiness / publication-export"
  contract.
- **Input**: a released item/version and its release-readiness (BOM/MBOM/routing/
  baseline/esign state).
- **Output**: a readiness report (and later a publication package) an external
  ERP adapter can consume.
- **Reuse (mandatory, no re-derivation)**: `latest_released_guard`,
  `suspended_guard`, and `ReleaseReadinessService.get_item_release_readiness()`.
- **Non-goals**: no purchase/sale order creation; no real-ERP connection; no Odoo
  runtime dependency; no GPL/AGPL code reuse; never bypass latest-released /
  suspended / release-readiness.

## 3. Contract the R1-A taskbook must lock

Grounded against `services/release_readiness_service.py`
(`get_item_release_readiness` returns `summary{ok,error_count,warning_count,
by_kind}`, `resources[]{kind,errors,warnings}` for `mbom_release` /
`routing_release` / `baseline_release`, and a separate `esign_manifest`):

- **publication-readiness is NOT a new readiness system.** R1-B must **wrap**
  `ReleaseReadinessService.get_item_release_readiness()` — it must not re-derive
  MBOM / routing / baseline readiness.
- **Eligibility formula (fixed):**
  - `eligible = latest_released_guard passes`
  - `AND suspended_guard passes`
  - `AND get_item_release_readiness(...).summary.ok == true`
  - `AND esign_manifest satisfies the sign-off-complete condition ratified in R1-A`
- **`blocking_reasons` come only from existing verdicts:** `not_latest_released`,
  `suspended`, `mbom_release`, `routing_release`, `baseline_release`, `esign`.
- **esign must be handled explicitly** — it is **not** covered by `summary.ok`
  because it comes from the separate `esign_manifest` field. **Default product
  decision: esign counts toward eligibility.** If the team instead treats esign
  as informational only, R1-A must simultaneously demote it from
  `blocking_reasons` to warnings/info. (The concrete "sign-off complete"
  predicate on `esign_manifest` is pinned in R1-A.)
- **`resources[].errors/warnings` map directly** to ERP publication blocks/hints;
  no fourth readiness semantics is invented.

## 4. R1-B implementation boundary (for a later, separately-opted slice)

- Proposed routes:
  - `GET /api/v1/plm-erp/items/{item_id}/publication-readiness`
  - (later, separable) `GET /api/v1/plm-erp/items/{item_id}/publication/export`
- Parameters must be explicit, with defaults echoed into the response (no silent
  hardcoding): `ruleset_id` (default `readiness`), `mbom_limit` (20),
  `routing_limit` (20), `baseline_limit` (20).
- R1 does **not** introduce tenant-level ruleset configuration; the default + any
  query override are written into the response.
- No purchase/sale order creation; no real-ERP connection; no Odoo runtime
  dependency; no GPL/AGPL reuse.

## 5. Router / test requirements (R1-B)

- The new router registers via the existing registration point — R1-B re-verifies
  whether that is `api/app.py` `include_router` or an existing registry at start
  of work (the comparison's route evidence spans `api/routers/` and
  `meta_engine/web/`).
- All `ValueError` / service-validation errors map to `HTTPException(...) from
  exc`, per the repo exception-chaining contract.
- R1-B tests must cover:
  - not latest released → blocked
  - suspended → blocked
  - readiness resource errors → blocked
  - esign incomplete → blocked
  - readiness warnings only → eligible with warnings
  - `ruleset_id` / limits passed through to `get_item_release_readiness`
  - unknown ruleset `ValueError` → chained `HTTPException`
  - no external ERP HTTP / write side effect
  - response contains no purchase/sale transaction

## 6. Phasing (each its own opt-in)

1. **R1-A taskbook** — lock the publication contract: eligible/blocked semantics,
   the eligibility formula above, the esign-complete predicate, the minimal
   payload (item / version / lifecycle / BOM-MBOM readiness / file refs /
   blocking_reasons), and the static/behavioral guard surface. External ERP
   adapter is explicitly a later track.
2. **R1-B readiness/export API** — the read-only routes in §4, wrapping
   `get_item_release_readiness` + the two guards; no external side effects.
3. **R2 adapter / outbox** — adapter interface + outbox with dry-run/replay; a
   real ERP connector is yet another taskbook.

## 7. Non-Goals (program-wide)

No ERP system in this repo; no Odoo dependency (Odoo is a comparison-semantics
source only); no purchase/sale transaction surface; no real-ERP connector in R1;
no GPL/AGPL code reuse; no bypass of latest-released / suspended / release-
readiness guards.

## 8. Status

Doc-only program plan. The comparison doc (#643) §5 gets a dated status
annotation on the G1/G2 rows only (no prose rewrite). The next step is the
**R1-A taskbook** (doc-only), which requires its own explicit opt-in; R1-B and R2
follow, each opted in separately.
