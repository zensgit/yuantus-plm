# PLM Collaboration Phase 7 — Governed Write-Back Seam (design-first)

Date: 2026-06-27
Type: **design-only**. Authorizes no build. Frames the decision surface for letting
a PLM user act on PLM data *from inside the MetaSheet embed* — and ties it to
reviewable exit criteria so the owner resolves the forks at a review gate before
any slice. Scope: the **MetaSheet BOM-review embed** write path only. It does NOT
spec the endpoint, the pact schema, or the UX — those are build, gated on this gate.

## 0. The load-bearing invariant (read this first)

**Identity continuity ≠ capability; and read ≠ write.** Two applications of the
same line:
1. A write is a **separate, write-scoped authorization** — it is **never** the
   read-only embed token. The shipped embed token is `typ:"embed"` with a read
   `feature_key`; it bootstraps a read handshake and must not escalate to a write.
   A write requires its **own** freshly-minted, **write-scoped, single-use,
   audited** token. Reusing the read handshake for a write silently breaches the
   invariant — this is the one place a blurred sentence becomes a real hole.
2. **"Write-back" in PLM means entering governed change control, not mutating a
   row.** The embedded surface stays the P3-A read-only projection by default; a
   write is an explicit, separately-gated, governed PLM operation.

## 1. What "write-back" actually targets

The embed renders the P3-A projection of **"Part BOM" Items** (relationship-Items:
`quantity` / `uom` / `find_num` / `refdes`), read-only via
`GET /api/v1/bom/multitable/{part_id}/context`. A "BOM write-back" would mutate a
**"Part BOM" Item** — which in PLM is a change subject to lifecycle / change
control, not a free-form row edit.

## 2. Current state — the existing governed write seams (factual; get this exact)

| Seam | Endpoint | Gate | Transactional | Audit | Pact |
|---|---|---|---|---|---|
| **ECO apply** (prod, primary) | `POST /api/v1/eco/{id}/apply` | `check_permission(execute/apply)` + ECO must be **APPROVED** + diagnostics pre-check + activity gate + version-lock + rebase-conflict | full commit/rollback | `EcoUpdatedEvent` + `AuditLogMiddleware` | **none** |
| **Workflow actions** (prod) | `POST /api/v1/workflow-actions/execute` | auth; permission **deferred to rule `match_predicates`**; per-rule `fail_strategy` (block/warn) | full rollback | middleware + runs table | **none** |
| **Helpdesk write-back** (prod; closest external-write precedent) | `POST /api/v1/breakages/{id}/helpdesk-sync/ticket-update` | auth + **lookup-as-boundary** (404 if missing); status allowlist | full rollback | **explicit `AuditLog` row + `event_id` idempotency** | **none** |
| Approval-automation ECO notify | `POST /api/v1/approvals/automation/eco/{id}/actions` | `require_admin_user` → `is_entitled` → allowlist | rollback (noop) | explicit `AuditLog` row | **none** |

Two facts that constrain everything below:
- **No existing write seam has a pact.** The MetaSheet write-back is cross-repo, so
  a **consumer-first write pact** (metasheet2 → provider verifier) is mandatory and
  is the **first gated build slice**.
- **Approval-automation notify is a STUB** (no real state mutation yet); it is not a
  working write seam — a real write-back must define its own governed path, while
  preserving the audit contract the stub already records.

**🚩 The bypass the design must forbid.** Direct BOM routes exist —
`POST/PUT/DELETE /api/v1/bom/tree/{parent}/children[/{child}]` (gated by "Part BOM"
`AMLAction.add/update/delete`) — but they have **no lifecycle/state guard**: a
*Released* part's BOM line is editable through them, and they don't rollback cleanly
on a permission error. **MetaSheet write-back MUST NOT use these.** The whole value
of the chosen seam is that it **enforces the change-control / lifecycle guard the
direct routes lack.**

## 3. Decision surface — forks and their *deciders*

### Fork 1 — Which governed seam (the central call)

- **(A) Route through ECO change control.** A BOM edit from the embed becomes part
  of an ECO and inherits the full governance: APPROVED-state, permission, diagnostics,
  version-lock, transactional apply, domain-event audit. Heavy, but every BOM change
  is a versioned, approved engineering change.
- **(B) A narrower lifecycle-guarded governed edit endpoint.** A new, purpose-built
  governed write that re-uses the permission + audit primitives and adds the
  **lifecycle guard the direct routes lack** (reject edits to a Released part's BOM,
  etc.), without the full ECO ceremony.

**Decider:** the **governance level BOM changes require** + the part's lifecycle
state. If BOM changes must be versioned/approved engineering changes → A. If a
lighter, lifecycle-guarded governed edit is acceptable for the embed's use case → B
(but B is net-new, so it carries the burden of proving it guards everything ECO apply
does). Do not pre-decide; this is the gate's call.

### Fork 2 — The write authorization (write ≠ read token)

A write rides the **already-shipped single-use model** (metasheet2 #2370,
`consumeEmbedJti`), but with a **write-scoped** token, not the read embed token. The
chain: `auth → is_entitled(<write feature_key>) → check_permission("Part BOM",
update) → lifecycle/state guard → governed apply (Fork 1) → audit + idempotency`.
The served-tenant cross-check (consumer `claims.tenant_id == adapter served tenant`)
is **inherited** from the read path (#2356). **Decider:** the write `feature_key` and
permission mapping (likely "Part BOM" `AMLAction.update`), confirmed by the owner.

### Fork 3 — The write pact (first build slice, not optional)

No seam has a pact today; a cross-repo write demands a **consumer-first pact**
(metasheet2 defines the write contract → Yuantus provider verifier in
`test_pact_provider_yuantus_plm.py` against `contracts/pacts/metasheet2-yuantus-plm.json`).
**Decider:** none — this is required; it's just sequenced first.

## 4. Two-repo boundary

| Repo | Owns | Does NOT |
|---|---|---|
| **YuantusPLM (provider)** | the governed write endpoint (Fork 1); validates `is_entitled` + permission + **lifecycle guard** + write-token scope/single-use; applies transactionally; audits with idempotency | does not trust a consumer-minted write token; does not expose the direct BOM routes to the embed |
| **metasheet2 (consumer)** | **relays the write INTENT** from the embed UI to the provider's governed endpoint with a write-scoped token; renders success/failure; never writes PLM directly | does not mint write tokens; does not bypass to direct BOM routes |

## 5. Acceptance criteria (mirror P3-D0 §5; design-first ⇒ reviewable now)

| Exit criterion | How the design satisfies it |
|---|---|
| Read token cannot write | A write requires a distinct **write-scoped** token; a `typ:"embed"` read token presented to the write endpoint → rejected (no capability escalation). |
| Unentitled → no write | `is_entitled(<write feature_key>)` gates before any mutation; unentitled → 403, nothing mutated. |
| Unpermitted → no write | `check_permission("Part BOM", update)` before mutation. |
| **Wrong lifecycle state → rejected** | The chosen seam enforces the change-control/lifecycle guard the direct BOM routes lack (e.g. Released part → rejected). |
| Cross-tenant → rejected | served-tenant cross-check inherited from the read path (#2356); token tenant ≠ served tenant → 403, pre-mutation. |
| Single-use / replay → unusable | write token consumed (`consumeEmbedJti`-style, #2370) before apply; replay rejected. |
| Audited + idempotent | explicit `AuditLog` row + an `event_id`-style idempotency key (the helpdesk precedent) so a retried relay/re-mint does not double-apply. |
| Failed write → full rollback | transactional apply (ECO apply / the new endpoint); a failed apply leaves **no partial state**. |
| No direct-BOM bypass | the embed write path routes only through the Fork-1 governed seam; the direct `bom/tree` routes are never exposed to it. |
| Read embed stays read-only by default | write is an explicit, separately-gated action; the default embed is unchanged. |

## 6. What this resolves for Phase 6 (the useful by-product)

Because a write-back is a **per-action governed call** that rides the existing
single-use model, **write-back does not by itself require a continuous session.** It
is therefore **removed as a Phase 6 trigger** — leaving only *bridge activation* and
*continuous-in-iframe UX* as the remaining triggers for the SSO/identity-session
spine (#880). This is narrow and deliberate: it does **not** say Phase 6 is
unnecessary; it says write-back no longer forces it, reusing what's already shipped
instead of inventing session infra.

## 7. Phasing (design → review gate → build; build NOT authorized here)

1. **This doc** — design + decision surface. **Review gate:** owner resolves Fork 1
   (seam), Fork 2 (write feature_key + permission), and confirms Fork 3 (pact-first).
2. *(gated)* **Slice 1 = the consumer-first write pact** (metasheet2) + provider
   verifier — the contract before the code.
3. *(gated)* Provider governed write endpoint (Fork 1) with the lifecycle guard +
   write-token scope/single-use + audit/idempotency; then the consumer relay + UI.

## 8. Open questions for the owner

1. **Governance level for embed BOM changes** → Fork 1 (ECO change-control vs narrower
   lifecycle-guarded edit).
2. **Write `feature_key` + permission mapping** (proposed: "Part BOM" `AMLAction.update`) → Fork 2.
3. Confirm **pact-first** sequencing (Slice 1) and the write-token = read-token-separation invariant.
4. Is write-back even the next thing to build, or does it stay scoped-but-parked until a customer needs in-embed editing? (Same reassess discipline as Phase 6 / VemCAD S5.)

## References (grounding)

- **Governed seams (Yuantus `origin/main`):** ECO apply `eco_impact_apply_router.py` / `eco_service.py:action_apply`; workflow actions `parallel_tasks_workflow_actions_router.py`; helpdesk write-back `parallel_tasks_router.py` (+ `AuditLog` idempotency); audit `api/middleware/audit.py`; entitlement `entitlement_service.py`; write target `bom_multitable_projection_service.py` ("Part BOM" Items); direct-BOM bypass `bom_tree_router.py`
- **Shipped read/handshake (do not redo):** offline verify + served-tenant + single-use — metasheet2 #2341/#2347/#2356/#2370; provider mint #733/#780
- **Pact boundary:** `contracts/pacts/metasheet2-yuantus-plm.json`, `test_pact_provider_yuantus_plm.py`
- **Companion:** Phase 6 SSO / identity-session spine design (#880); P3-D0 embed-spine scope (#730); backlog lines 2/3/4 roadmap (#882)
