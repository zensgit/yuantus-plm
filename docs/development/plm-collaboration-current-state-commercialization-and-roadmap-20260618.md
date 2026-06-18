# PLM Collaboration Current State, Commercialization, And Roadmap

**Date:** 2026-06-18
**Status:** current-state and decision ledger. This document consolidates the live status of the
Yuantus PLM x MetaSheet collaboration line, the monetization answer, and the maintainability plan.
It does not authorize implementation. Each follow-up remains a separate owner opt-in.

This document supersedes only the stale status/TODO portions of older planning docs. It does not
replace the historical scope packages, verification closeouts, pact docs, or design invariants.

---

## 0. Reading Order And Authority

Use this file as the current entry point for the PLM x MetaSheet commercialization and maintenance
line.

| Document | Current role |
|---|---|
| `docs/development/plm-collaboration-automation-development-plan-20260602.md` | Canonical product architecture, red lines, decision gates, and Phase 0-6 structure. Its checkboxes and "implementation not started" status are historical and stale. |
| `docs/DEVELOPMENT_PLM_COLLABORATION_PHASE0_SCOPE_MAPPING_TASKBOOK_20260602.md` | Historical Phase 0 grounding and taskbook. P0-A/P0-B runtime flag and compose seam work has since partially landed. |
| `docs/DEVELOPMENT_PLM_COLLABORATION_PHASE2_APPROVAL_AUTOMATION_CLOSEOUT_20260604.md` | Still authoritative for the Phase 2 approval-automation skeleton: SKU/templates/ECO projection/NOTIFY stub/capability entry landed; execution engine deferred. |
| `docs/development/plm-collaboration-phase3-bom-multitable-scope-20260605.md` | Phase 3 BOM multi-table scope/design package and read-only/write-back red lines. |
| `docs/development/plm-collaboration-phase3d-embed-spine-scope-20260605.md` | P3-D0 scope and acceptance framing for the embed spine. Historical now that P3-D has landed. |
| `docs/development/plm-collaboration-phase3d-embed-spine-closeout-20260606.md` | Historical P3-D closeout. Superseded on the two #737 partials by the later delivery doc. |
| `docs/development/plm-collaboration-phase3d-embed-delivery-and-verification-20260609.md` | Latest P3-D delivery/verification record. Provider mint and MetaSheet token-bound offline viewer are merged; PLM parent-page host is still deferred. |
| `docs/DEV_AND_VERIFICATION_METASHEET_YUANTUS_PACT_CLOSURE_20260411.md` and `docs/DEV_AND_VERIFICATION_METASHEET_YUANTUS_PACT_SYNC_HELPER_20260411.md` | Pact history and sync helper for the older protected REST surface. They do not yet cover every modern collaboration/embed surface. |

---

## 1. Live Phase Status

| Phase | Live status as of 2026-06-18 | Commercial meaning |
|---|---|---|
| P0 Scope & Mapping | Partially landed. The runtime/product-layer seam and combined-profile shape exist, but this remains a boundary layer rather than a finished product surface. | Enough to keep the collaboration line in one codebase with gates; not itself sellable. |
| P1 Entitlement Core | Partially landed and actively used. `is_entitled` is the single gate, with tenant scoping and offline signed-license import already established. | Foundation for paid features exists. Commercial ops are still incomplete: seat/quantity accounting, renewal/grace, vendor issuance tooling, and admin UX remain follow-ups. |
| P2 Approval Automation | Skeleton landed and closed: independent SKU, draft templates, ECO governed projection, NOTIFY stub, and capability entry. The real execution engine is deliberately deferred. | Can demonstrate an upgrade path, but should not be sold as an automation engine yet. |
| P3 BOM Multitable + Embed Spine | Backend/provider and consumer-viewer halves are live. P3-A/P3-B/P3-D1 are on Yuantus; P3-C/P3-D2 plus tenant cross-check and jti single-use are on MetaSheet2. #780 records the closed backend/embed delivery. The PLM parent-page host that mints, iframes, and posts tokens is still deferred. | This is the strongest near-term paid feature: read-only BOM review/collaboration, with governed projection, entitlement, short-lived embed tokens, tenant checks, and one-use consumer gating. |
| P4 Workbench | Not started. | No paid promise yet. |
| P5 Controlled Write-Back | Not started. Write-back remains a hard red line unless routed through `/aml/apply` or governed `/actions`. | Do not sell editable PLM write-back yet. |
| P6 Enterprise Hardening | Not started as a complete phase. Pieces exist in P1/P3, but SSO identity spine, offline-license operations, seats, retries/circuit breaking, observability, bridge activation, and admin revocation remain open. | Required before broad enterprise/self-serve scale. |

---

## 2. Monetization Answer

Yes: the PLM multi-dimensional table line can be a paid product, but the sellable wedge should be
precise.

Recommended paid offer now:

- **PLM BOM Review Add-on / Collaboration Pro, controlled enterprise sale.**
- Sell the read-only BOM review table, governed PLM projection, MetaSheet collaboration surface,
  and entitlement/offline-license capability.
- Scope it as a deployment-assisted add-on, not self-serve billing.

Do not lead with:

- "Approval automation" as a finished product. P2 is a skeleton plus NOTIFY stub, not an execution
  engine.
- Editable spreadsheet-to-PLM write-back. P5 is explicitly not built.
- Fully embedded PLM click-through. The provider mint and consumer viewer exist, but the PLM
  parent-page host remains deferred.

Commercial gaps before broad selling:

1. Vendor-side license issuance CLI/runbook and key custody.
2. License quantity/seats/grace/renewal semantics.
3. Admin UX for license import/status and feature availability.
4. Multi-`kid` verification so key rotation does not require a flag day.
5. Product compatibility matrix and cross-repo gate for the modern PLM x MetaSheet surfaces.
6. A clear support boundary for offline installs: no online billing dependency in the first paid
   shape.

---

## 3. Maintainability Answer

MetaSheet can maintain or update its own product without constantly breaking Yuantus PLM, because
the integration is intentionally one-way and boundary-based:

- Yuantus remains the PLM source of truth.
- MetaSheet consumes governed projections and capability/embed contracts.
- The PLM base product does not import MetaSheet runtime code.
- Existing pact discipline already protects a large older REST surface.

However, "low runtime coupling" is not the same as "zero integration risk." The combined paid
product still needs explicit compatibility gates for the newer collaboration surfaces:

- `GET /api/v1/integrations/capabilities`
- `GET /api/v1/bom/multitable/{part_id}/context`
- `POST /api/v1/bom/multitable/{part_id}/embed-token`
- the MetaSheet relay/embed routes and the `bom_multitable` payload shape

MetaSheet2 PR #2875 is the right direction for this line: it hardens the BOM inner-shape guard so
silent field drift is rejected instead of degrading into blank UI cells. As of this document, that
PR is still an upstream owner-gated/open item, not yet a Yuantus mainline fact. Once merged, it
should be treated as a prerequisite proof point for the "no silent field drift" claim.

---

## 4. Recommended Sequence

### A. Maintainability Hardening First

1. Land the MetaSheet2 all-field BOM shape guard (#2875 or successor).
2. Extend the contract/pact/golden-schema coverage to the modern surfaces listed in §3.
3. Add a sync/check gate so Yuantus and MetaSheet cannot drift silently on those surfaces.
4. Support multiple embed-token key IDs on the consumer side before rotation is needed.

### B. Monetization In Three Steps

1. **Manual offline enterprise sale.** Use signed offline license import and deployment-assisted
   enablement. This is the lowest-risk way to charge for BOM review.
2. **Offline commercial operations.** Add vendor issuance tooling, seats/quantity, grace/renewal
   policy, and admin status UI.
3. **Online activation/billing later.** Only after the offline enterprise shape is stable.

### C. Product Follow-Ups

1. PLM parent-page embed host: mint token, host iframe, post token with origin pinning.
2. SSO/identity-session spine. This also unlocks MetaSheet bridge activation and a real revocation
   model beyond short TTL plus one-use jti.
3. P2 execution engine if "Automation Enterprise" is to become a real product.
4. P4 workbench, P5 controlled write-back, P6 enterprise hardening, each as a separately gated line.

---

## 5. Decision Gates To Keep Open

| Gate | Recommended default |
|---|---|
| Offline vs online license for local deployments | Offline first. Local customers should not need online payment/activation for already-purchased features. |
| MetaSheet deployment shape | Bundle per deployment profile; keep base Yuantus integration-unaware unless explicitly opted in. |
| SKU shape | Start with a master collaboration switch plus independent feature keys (`bom_multitable`, `approval_automation`). Split finer only when sales/support needs it. |
| Write-back | No table-cell direct write-back. Future writes only through `/aml/apply` or governed actions with version, lifecycle, esign, approval, and audit checks re-run. |
| Revocation | Current embed design uses short TTL plus one-use jti. Admin revocation is cross-repo/SSO-gated and should not be modeled as a Yuantus-only table. |

---

## 6. What This Consolidation Changes

This document does three things:

1. Marks old planning checkboxes as historical without deleting their design value.
2. Separates "paid now, with controlled scope" from "enterprise/self-serve hardening later."
3. Narrows the maintainability claim: PLM runtime/source coupling is low, but product compatibility
   still needs modern-surface gates and upstream guardrails.

It deliberately does not collapse the historical docs into one large file. Those docs remain useful
because they preserve slice-by-slice decisions, proof, and red lines.
