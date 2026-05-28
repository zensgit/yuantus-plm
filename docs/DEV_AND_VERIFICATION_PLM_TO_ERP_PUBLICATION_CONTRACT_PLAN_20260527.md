# DEV & Verification: PLM→ERP Publication Contract Plan

Date: 2026-05-27

Records the doc-only delivery of
`DEVELOPMENT_PLM_TO_ERP_PUBLICATION_CONTRACT_PLAN_20260527.md` — the program plan
for the OdooPLM comparison's **G2** gap (PLM→ERP downstream surface). This PR is
**doc-only**: no code, no API, no R1-A taskbook. It scopes the program and pins
the contracts the R1-A taskbook must lock.

## 1. What changed

- New `DEVELOPMENT_PLM_TO_ERP_PUBLICATION_CONTRACT_PLAN_20260527.md` (program plan).
- This DEV/verification record.
- Two sorted entries in `DELIVERY_DOC_INDEX.md`.
- A dated status annotation on the comparison doc's §5 G1/G2 rows only
  (`DEVELOPMENT_ODOOPLM_GROUNDED_COMPARISON_20260525.md`) — no §0/§5 prose rewrite.

## 2. Grounding verified (against current main `167d9661`)

The plan's reuse primitives and the eligibility formula were checked against the
real code before drafting:

- `services/release_readiness_service.py` — `ReleaseReadinessService.get_item_release_readiness(item_id, ruleset_id, mbom_limit, routing_limit, baseline_limit)` returns a Dict with:
  - `summary{ ok (== error_count==0), resources, ok_resources, error_count, warning_count, by_kind }`,
  - `resources[]{ kind, resource_type, resource_id, name, state, ruleset_id, errors, warnings }` where `kind ∈ {mbom_release, routing_release, baseline_release}`,
  - a separate `esign_manifest` (via `get_esign_manifest_status`).
- `services/latest_released_guard.py` and `services/suspended_guard.py` exist.
- No existing `plm-erp` / `publication` router → the proposed routes do not collide.

So the eligibility formula's fields (`summary.ok`, `resources[].kind`,
`esign_manifest`) and the `blocking_reasons` taxonomy are all real. The esign
field being **separate** from `summary` is exactly why the plan handles esign
explicitly (not via `summary.ok`).

## 3. Scope / boundaries

- Outbound publication contract only — no ERP system, no Odoo dependency, no
  purchase/sale transaction surface, no real-ERP connector in R1, no GPL/AGPL
  reuse, no bypass of latest-released / suspended / release-readiness.
- Phasing: R1-A taskbook → R1-B readiness/export API → R2 adapter/outbox, each
  separately opted in.

## 4. Verification (this doc-only PR)

- doc-contract pytests (delivery-doc-index references + sorting, runbook-index
  completeness, DEV/verification index completeness + sorting, claude-assist
  discipline, p6 plan gate, doc-index sorting) — pass.
- `verify_lisp_shell_static.py` 28, `verify_bridge_static.py` 13,
  `verify_material_sync_static.py` pass (unchanged — no client/helper change).
- `git diff --check` clean.

## 5. Status

Doc-only program plan delivered. Next step is the **R1-A taskbook** (doc-only,
separate opt-in), which locks the publication contract incl. the esign
sign-off-complete predicate. No code is authorized by this PR.
