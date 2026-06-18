# PLM Collaboration & Automation Edition — Phase 2 (Approval Automation) Closeout

**Date:** 2026-06-04
**Status:** CLOSED — minimal sellable approval-automation skeleton on `main`; execution engine deliberately NOT pulled in.
**Scope:** YuantusPLM (`zensgit/yuantus-plm`), Phase 2 of the PLM Collaboration & Automation Edition.

> **Current-status note (2026-06-18):** This remains authoritative for the
> Phase 2 skeleton: independent SKU, draft templates, ECO governed projection,
> NOTIFY stub, and capability entry are closed; the real execution engine is
> still deferred. Use
> `docs/development/plm-collaboration-current-state-commercialization-and-roadmap-20260618.md`
> for the live cross-phase status and commercialization plan.

This closeout fixes the product/technical invariants the four Phase 2 slices established,
so a later execution-engine slice or Phase 3 (BOM multi-table) does not re-litigate them.

---

## 1. Landed slices

Phase 2 was cut into four owner-ratified, narrow slices. All are squash-merged on `main`:

| Slice | PR | Merge commit | What landed |
|---|---|---|---|
| **P2-A** feature gate (independent SKU) | #708 | (in `2747cb16`) | `approval_automation` lit as a separately-sellable SKU |
| **P2-B** template registry + provisioning | #708 | `2747cb16` | `meta_approval_automation_templates` table + admin/entitlement-gated idempotent DRAFT provisioning |
| **P2-C** ECO governed projection + notify stub | #710 | `dbbfd05f` | read-only ECO→approval-context projection + governed NOTIFY stub |
| **P2-D** scenario capability/upgrade entry | #712 | `c493210d` | ungated scenario-level capability/upgrade affordance entry |

> P2-A and P2-B shipped in a single PR (#708). The owner ordered the first cut as
> "authorization gate + template skeleton" before any scenario wiring.

Phase 2 builds directly on Phase 1 (Feature Entitlement Core): P1-A #699 data model,
P1-B #700 check kernel, P1-C #703 offline Ed25519 license verify, P1-D #705 upgrade
affordance.

---

## 2. Product boundary (what the skeleton is — and is not)

The product ladder, deliberately stopping short of an execution engine:

1. **Sellable** — `approval_automation` is an **independent SKU** (`plm.approval_automation`),
   NOT bundled into `plm.collab` and NOT reusing `plm_collaboration_pro`. It can be sold
   separately and bundled later.
2. **Provisionable** — an admin can provision **DRAFT** approval-automation templates for
   three PLM scenarios (ECO approval, BOM-change approval, document-release approval).
   Provisioning is idempotent and concurrency-safe; it never enables or executes.
3. **Readable** — the first scenario (ECO) is wired to a **read-only governed projection**
   of an ECO into an approval context (`GET .../eco/{eco_id}/context`) plus a governed
   **NOTIFY stub** action (`POST .../eco/{eco_id}/actions`).
4. **Discoverable entry** — a scenario-level **capability / upgrade entry**
   (`GET .../eco/capabilities`): entitled tenants see what automation they can do,
   unentitled tenants see an upgrade affordance.

**Out of scope by design (NOT built):** a real automation/execution engine, real DingTalk
dispatch, any write-back to PLM authoritative fields or approval state, a flow editor.
The existing approval bridge (`/sync/plm`, `/actions`, `dispatchPlmAction`, DingTalk) lives
entirely on the MetaSheet side (`ApprovalBridgeService.ts` / `routes/approvals.ts`) and is
already a closed loop (pull Yuantus `GET /eco` → write-back Yuantus `/eco/:id/approve|reject`,
PLM is the source of truth). Phase 2 is the Yuantus-side contribution onto that bridge.

---

## 3. Authorization invariants (every future feature gate must honor)

- **Single judgment path.** A feature is available iff
  `EntitlementService.is_entitled(feature_key)` (`meta_engine/app_framework/entitlement_service.py`).
  Never add a second license-read path; never query `AppLicense` directly elsewhere; never
  read `license_data` for authorization (it is a marker only).
- **Single tenant scoper.** Every license read goes through
  `license_scope.resolve_license_scope()` (tenant from request context; falls back to
  `"default"` ONLY in `TENANCY_MODE=single`, else raises — no silent global license).
  `tenant_id` filters; `org_id` is recorded only; a `tenant_id IS NULL` legacy license never
  unlocks.
- **Real authorization = P1-C signed license.** Production authorization always flows through
  the P1-C Ed25519 **offline signed license import** (`license_import_service` /
  `yuantus license import`): the vendor signs with a private key that is NEVER in the repo;
  the deployment verifies against a `LICENSE_PUBLIC_KEYS` allowlist (kid rotation) over
  canonical JSON.
- **Mock is demo-only.** The P1-D `POST /features/{key}/mock-activate` route is superuser-only
  and DEFAULT-OFF; it is NEVER a production authorization write path. P2-D surfaces this
  explicitly to clients as `upgrade.mock_activation = "demo_only"` and
  `upgrade.license_mode = "offline_signed"` (read-only hints; no new write path).

---

## 4. Security invariants

- **Write endpoints are admin-first, then entitlement.** A tenant-config WRITE
  (P2-B `POST .../provision`, P2-C `POST .../eco/{eco_id}/actions`) runs
  `require_admin_user` (identity — who may mutate tenant config; unauth→401, non-admin→403)
  FIRST, THEN `is_entitled` (SKU — admin-but-unentitled→403 upgrade, with ZERO audit
  written). Entitlement answers "bought?", never "who may write?".
- **Read projections gate before they touch data.** P2-C `GET .../eco/{eco_id}/context`
  pins the order authenticate → `is_entitled` → ONLY THEN query the ECO. An unentitled caller
  receives a null-context affordance and the ECO is **never queried**, so object existence is
  not leaked (an existing and a non-existent id return identical responses — pinned by a test
  asserting `existing == missing`).
- **Defense in depth on writes.** The provision service re-asserts `is_entitled` itself, so a
  non-router caller cannot bypass the gate; concurrent provisioning catches `IntegrityError`,
  rolls back and re-reads (a lost race never 500s, never duplicates).
- **Curated read-only projection.** The ECO projection exposes only approval-context fields
  and version display labels; it deliberately excludes writable authoritative machinery
  (`source_version_id` / `target_version_id`, BOM/routing change payloads). A test pins the
  absence of the version IDs.
- **Pure-affordance surfaces stay data-free.** The P2-D capability entry is scenario-level
  (no `eco_id`), never queries an ECO, and performs no write. A SOURCE-LEVEL test
  (`test_p2d_code_has_no_eco_lookup_or_write`) reads the P2-D service + router source and
  asserts `get_eco` / `ECOService` / `ECOApproval` / `AuditLog` / `.add(` / `.commit(` are all
  absent, pinning the boundary against future drift.

---

## 5. Route surface

Base PLM app route count pin: **698**.

| Step | Δ | Routes added |
|---|---|---|
| Phase 1 P1-D | 691 → 693 | `GET /features/{key}`, `POST /features/{key}/mock-activate` |
| Phase 2 P2-B | 693 → 695 | `GET /approvals/automation/templates`, `POST /approvals/automation/provision` |
| Phase 2 P2-C | 695 → 697 | `GET /approvals/automation/eco/{eco_id}/context`, `POST .../actions` |
| Phase 2 P2-D | 697 → 698 | `GET /approvals/automation/eco/capabilities` |

The authoritative pin lives in `test_phase4_search_closeout_contracts.py` (the only route-count
pin the CI `contracts` job runs via the enumerated list). Three secondary pins
(`test_metrics_router_route_count_delta`, `test_breakage_design_loopback_metrics`,
`test_tier_b_3_breakage_design_loopback_portfolio_contract`) and the
`/api/v1/approvals/*` owner registry in `test_approvals_router_decomposition_closeout_contracts`
are kept in lockstep. Phase 2 **intentionally changed the app route surface** by adding
unconditional affordance/capability routes; runtime behavior remains entitlement-gated, so
unentitled tenants receive upgrade/null/stub affordances instead of PLM data or writes. (This is
distinct from the Phase 0 / P0-A MetaSheet bridge seam, which is conditionally mounted on
`ENABLE_METASHEET` and so leaves the base route surface unchanged when the flag is off — that
"flag-off surface unchanged" framing does NOT apply to the Phase 2 routes.)

---

## 6. Next-stage recommendation (risk-ranked)

Two candidates remain; they are NOT equal risk.

- **Execution engine** (turn the NOTIFY stub / projection into real automation): **moderate
  risk, well-bounded.** It builds on a stable, single judgment path and an already-complete
  MetaSheet-side bridge. The main new surface is real dispatch (DingTalk / reminders /
  escalation) and the governed write-back contract — but write-back already exists
  (ECO approve/reject via the bridge), so the engine consumes existing governed endpoints
  rather than inventing new authoritative writes. Recommended as the lower-risk next step if
  the goal is to make the sold capability actually run.

- **Phase 3 — BOM multi-table** (collaborative multi-dimensional BOM tables in MetaSheet
  referencing PLM part numbers): **highest risk.** Per the canonical plan it depends on the
  identity/embed spine, SSO, the read-only BOM projection (governed snapshot + version
  validation), and permission synchronization — the largest pile of unknowns. The canonical
  order is explicit: offline licensing → approval automation → **BOM multi-table last**.
  Recommended to be preceded by its own design/scope phase, not started directly on prediction.

**Recommendation:** if continuing the approval-automation line, the execution engine is the
lower-risk, higher-immediate-value next slice. Phase 3 BOM multi-table is the heavier bet and
should open with a design/scope cut. Either choice is a new phase and requires its own explicit
owner opt-in.

---

## References

- Canonical plan: `docs/development/plm-collaboration-automation-development-plan-20260602.md`
- Phase 0 scope mapping: `docs/DEVELOPMENT_PLM_COLLABORATION_PHASE0_SCOPE_MAPPING_TASKBOOK_20260602.md`
- Entitlement kernel: `src/yuantus/meta_engine/app_framework/entitlement_service.py`
- Approval-automation service/router (P2-B): `src/yuantus/meta_engine/services/approval_automation_service.py`, `src/yuantus/meta_engine/web/approval_automation_router.py`
- ECO projection/notify (P2-C): `src/yuantus/meta_engine/services/approval_automation_eco_service.py`, `src/yuantus/meta_engine/web/approval_automation_eco_router.py`
- Capability entry (P2-D): `src/yuantus/meta_engine/services/approval_automation_capabilities_service.py`, `src/yuantus/meta_engine/web/approval_automation_capabilities_router.py`
