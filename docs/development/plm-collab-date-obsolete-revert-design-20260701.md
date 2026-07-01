# Date-Obsolete Revert — Governance Decision Record (2026-07-01)

**Status:** DESIGN-FIRST governance decision document — authorizes no build.
**Ratification required before any code.** This is a **decision doc**, not an
implementation. It mirrors the sibling Phase 7 locked-BOM ECO-revision decision
doc (`plm-collab-phase7-locked-bom-eco-revision-route-design-20260630.md`, `#931`).
**Date:** 2026-07-01
**Baseline:** Yuantus `origin/main` at `464cf998` (`#931`).

> **Provenance.** Produced autonomously as the second Group B design-first item
> the operator directed ("请帮我执行", after ratifying the order "先合 #931"). It is a
> **decision doc for owner ratification**, not authorization to build; a clean,
> single-revert, docs-only unit. Every code reference was verified against
> `origin/main` (`git show origin/main:<path>`). The recommended defaults in §3 are
> the author's engineering recommendation and **remain pending owner ratification** —
> none decides governance semantics on the owner's behalf.

This record exists because "Date-obsolete revert" is classified as a **Governance
design gate** — it "Mutates acknowledged / worker-derived state. Needs explicit
revert semantics and audit model before code"
(`plm-collab-remaining-gated-development-order-and-verification-20260630.md:41`),
and the TODO closeout independently records it as Deferred pending "an explicit
governance decision" (`plm-collab-remaining-todo-dev-verification-20260630.md:114`).

---

## 1. Purpose & Scope

### Purpose

The date-obsolete subsystem today can only move state **forward**: a worker
raises impact flags and (on the version-scoped path) promotes an expired child
Item to lifecycle `Obsolete`; an admin can `acknowledge` an impact flag. There is
**no revert/undo anywhere in the feature**. This document defines what "revert"
should *mean*, how it should be *authorized*, and how it should be *audited*, so
the owner can ratify one coherent semantics **before** any code is written.

### In scope

- Defining the *meaning* and *blast radius* of "revert" for date-obsolete state (DP1).
- Defining the *authorization* tier for a revert write (DP2).
- Defining the *audit model* and *idempotency/reversibility* of a revert (DP3).
- A design-only phase outline that applies **only if** the owner ratifies.

### Out of scope (not decided or built here)

- Any code, migration, route, or schema change. This is design-first.
- BOM-line (item_id-scoped) effectivity handling beyond flag-clearing — BOM-line
  effectivities remain out of scope (`DEV_AND_VERIFICATION_CADPDM_C3_DATE_OBSOLETE_WIRING_20260618.md:45`).
- Cascade / depth>1 propagation — propagation is FLAG-only, depth-1, never cascade
  (`DEV_AND_VERIFICATION_CADPDM_C3_DATE_OBSOLETE_MECHANISM_20260618.md:9`).
- Re-opening / extending the underlying effectivity `end_date` itself (see Open Questions).
- The pre-existing `find_effective_version` NULL-start narrowness — a separate,
  untouched fix (`…WIRING_20260618.md:48`).

---

## 2. Current State (grounded)

### 2.1 The impact entity and its two orthogonal state axes

The persisted entity is `DateObsoleteImpact` → table `meta_date_obsolete_impacts`
(`models/date_obsolete.py:32,35`). One row = one **depth-1 where-used PARENT**
flagged because a **CHILD's** date effectivity expired; it is advisory, never a
lifecycle transition on the parent (`date_obsolete.py:1-9`). (Note the direction:
the *child* whose effectivity expired is what gets obsoleted-or-marked; its depth-1
where-used *parents* are only flagged — never cascaded.) Idempotency is keyed on
`UniqueConstraint(effectivity_id, parent_item_id)` (`date_obsolete.py:57-61`;
migration `c3_date_obsolete_001:36-72`).

A row carries **two orthogonal state axes**:

- **(a) the flag's own review lifecycle** — `state` = `'open' → 'acknowledged'`
  (`date_obsolete.py:47-48`; allowed set `_IMPACT_STATES = {'open','acknowledged'}`,
  `ops_router.py:30`). There is no `'closed'`/`'reopened'` state.
- **(b) `child_obsoleted` Boolean** — records whether the CHILD Item was promoted
  to lifecycle `Obsolete` vs merely marked (`date_obsolete.py:43-45`).

### 2.2 Who writes what

- **Worker** (`services/date_obsolete_worker.py`) writes **nothing** to the impact
  table directly. It is a gated poller/drainer: it checks the global kill-switch
  `DATE_EFFECTIVITY_OBSOLETE_ENABLED` and the per-tenant entitlement
  `cadpdm_date_obsolete`, then delegates each expired effectivity to
  `DateEffectivityObsoleteService.process_expired` (`worker.py:100-108`).
- **Service** (`date_effectivity_obsolete_service.py`) does all derivation. On
  insert, `_upsert_impact` writes `effectivity_id`, `child_item_id`,
  `parent_item_id`, `child_obsoleted`, `reason`, `properties`, plus `state='open'`
  + `detected_at=now` (`service.py:238-247`). On **re-scan** of the same
  `(effectivity_id, parent_item_id)` row, `child_obsoleted` + `reason` +
  `properties` are overwritten **together** (`service.py:234-236`), but `state` and
  `acknowledged_*` are **left untouched** — so re-scan never clobbers a human
  acknowledgement.
- **Ops router** (`web/date_obsolete_ops_router.py`) is the only human-write
  surface. `acknowledge` sets `state='acknowledged'`, `acknowledged_at=utcnow()`,
  `acknowledged_by_id=user.id`, only when `state != 'acknowledged'` (single:
  `ops_router.py:256-260`; batch: `ops_router.py:213-219`). These three fields are
  the **only** fields a human action mutates.

### 2.3 Child-obsolete promotion (a side effect OUTSIDE the table)

On the version-scoped path `_process_version_expired` (`service.py:120-181`), the
service computes `has_effective` and `already_obsolete = (item.state == 'Obsolete')`
(`service.py:136-137`). If `apply_obsolete AND NOT has_effective AND NOT
already_obsolete`, it calls `LifecycleService.promote(item, 'Obsolete', user_id,
comment='date effectivity expired (C3 auto-obsolete)')` (`service.py:141-148`).
This is a **real Item lifecycle transition, a side effect outside the impact
table.** The impact row records **no prior lifecycle state** — only the
`child_obsoleted` boolean.

Reason codes (`service.py:160-165,194`): `child_obsoleted` (promoted this run OR
already `Obsolete`), `child_obsolete_failed` (promote errored; error in
`properties.obsolete_error`; **no** state change to undo),
`child_effectivity_expired` (still has an effective version; mere mark,
`child_obsoleted=False`), `bom_line_effectivity_expired` (BOM-line path
`_process_bom_line_expired` `service.py:253-320` NEVER promotes; flag-only).

### 2.4 Acknowledge, and the absent revert

Two admin-only endpoints transition `open → acknowledged` idempotently (`if
row.state != 'acknowledged'`): single (`ops_router.py:243-260`) and batch
(`ops_router.py:192-224`). The state machine is **strictly one-directional**. A
grep across all date_obsolete files for
`revert|reopen|un-obsolete|un-acknowledge|restore|rollback` returns only a DB
`session.rollback()` (`worker.py:115`) and the export docstring's negative
assertion that it "never acknowledges, reverts, or re-runs" (`ops_router.py:157-159`).
**No reverse/undo transition exists anywhere in the feature.**

### 2.5 Two facts that constrain any revert design (verified)

- **`child_obsoleted=True` is ambiguous about history.** It is `True` both when
  THIS run promoted the Item (`child_obsoleted = bool(result.success)`,
  `service.py:149`) **and** when the Item was ALREADY `Obsolete` before this expiry
  (`already_obsolete` branch, `service.py:137-138`; promote gated on `not
  already_obsolete`, `service.py:141`). A revert keyed on `child_obsoleted=True`
  alone would **over-revert** Items the worker never touched.
- **The impact table alone cannot reconstruct the Item's prior lifecycle state.**
  Promotion is done via `LifecycleService.promote` and the row stores no prior
  state. Whether `promote` itself is reversible / writes recoverable history lives
  in `yuantus.meta_engine.lifecycle.service` and is **not inspected here** (Open Question).

---

## 3. Decision Points Requiring Owner Ratification

Each recommendation is **recommended, pending owner ratification**.

### DP1 — What does "revert" MEAN / what is its scope?

The plan enumerates exactly four candidate semantics, framed as alternatives the
owner picks among
(`plm-collab-remaining-gated-development-order-and-verification-20260630.md:111`):
"Owner ratifies whether revert means reopen impact only, undo acknowledge only,
undo child obsolete promotion, or create a superseding correction event."

| Option | What it touches | Blast radius | Undo-ability |
|---|---|---|---|
| (i) Reopen impact only | `state`: `acknowledged → open` | Local to the impact row's review axis | Trivially reversible (re-acknowledge) |
| (ii) Undo acknowledge only | Clear `acknowledged_at`/`acknowledged_by_id`, set `state='open'` | Local to the impact row's ack fields | Trivially reversible |
| (iii) Undo child-obsolete promotion | Reverse the Item `Obsolete` transition; reconcile `child_obsoleted`/reason | **Item lifecycle state — outside the table**; interacts with re-scan | Hard; depends on whether `LifecycleService.promote` is reversible and audited |
| (iv) Superseding correction event | Append a new event that supersedes prior state; mutate/delete nothing | New append-only record; readers interpret latest | Reversible by appending again |

**Composability.** The plan presents these as a single ratified choice (pick ONE).
Analytically: (i) and (ii) are **near-duplicates** on the same review axis (both
move a row backward out of `acknowledged`) and are best treated as one
"reopen/un-acknowledge" family; (iii) is on a **different axis** (the Item
lifecycle side effect), strictly larger, and could be *composed* with (i)/(ii);
(iv) is an **orthogonal audit strategy** (append vs mutate) that could *implement*
any of (i)–(iii).

**Load-bearing tradeoff — worker instability.** (i)/(ii) are cheap and local to
`DateObsoleteImpact`. (iii) is the semantically hard case: it crosses out of the
impact table into Item lifecycle, cannot be reconstructed from the row (§2.5), must
reconcile the reason-code taxonomy, and — critically — is **not stable against the
polling worker**: because `_upsert_impact` refreshes `child_obsoleted`/`reason`
every tick (`service.py:234-236`), a revert that clears `child_obsoleted` while the
effectivity stays expired will be **recomputed and potentially re-promoted on the
next tick**. (iv) is the append-only-friendly choice, aligning best with the
standing append-only/idempotent + forensic invariants.

**RECOMMENDED default (pending owner ratification):** ratify a **two-tier**
meaning, not a single conflated one:

- Adopt **(iv) superseding correction event as the audit mechanism**, used to
  implement a **(i)/(ii) "reopen + un-acknowledge" review-flag revert** as the
  first shippable scope. It moves the row backward out of `acknowledged` by
  *appending* a correction event (no destructive mutation of `acknowledged_*`
  history) — the smallest, safest, worker-stable change, matching the existing
  append-only/idempotent convention (`…DATE_OBSOLETE_IMPACTS_FORK_B_20260627.md:19-22`).
- **Defer (iii) undo child-obsolete promotion** to a separate, later ratification:
  it requires resolving whether `LifecycleService.promote` is reversible/audited,
  the `child_obsoleted=True` ambiguity (§2.5), and worker re-promotion stability —
  none decided here.

### DP2 — How is revert AUTHORIZED?

| Option | Precedent | Tradeoff |
|---|---|---|
| Reuse `require_admin_permission` (admin/superuser role) | All six current ops routes use it (`auth.py:310-324`) | Symmetric with acknowledge; but revert is strictly more powerful |
| Superuser-only | Forensic summary/drill-down/export are superuser-only (`plm-collab-remaining-todo-dev-verification-20260630.md:28-29`) | Tighter; matches the "forensic" gravity of undoing worker-derived state |
| New entitlement (`cadpdm_date_obsolete_revert`) | Worker is already entitlement-gated (`cadpdm_date_obsolete`) | Most precise; but net-new policy — no finer-grained ops entitlement exists today |

**RECOMMENDED default (pending owner ratification):** for a DP1 (i)/(ii)
review-flag revert, reuse `require_admin_permission` (mirror acknowledge — the
review axis is already admin-writable, no escalation warranted); for any DP1 (iii)
undo-promotion revert, gate at **superuser-only**, consistent with the
"forensic surfaces are superuser-only" invariant, because it reverses a real Item
lifecycle transition. The docs do not specify the tier (Open Question).

### DP3 — How is revert AUDITED, and kept idempotent / reversible?

Today `acknowledge` records only `acknowledged_at`/`acknowledged_by_id`; the model
has **no** `reverted_by`/`reverted_at` columns (`models/date_obsolete.py`), so any
persisted revert-audit implies a **schema/migration**. The gate explicitly pairs
revert with a required "audit model" (`…gated-development-order-…:41`).

- **In-place mutation** — flip `state` back, null the ack fields. Simplest; but
  **destroys history** and cannot answer "was this ever acknowledged?" — conflicts
  with the forensic posture.
- **Add revert columns** — `reverted_at`/`reverted_by_id` (+ optional reason).
  Preserves the last ack actor but only one generation of history.
- **Append-only correction event (DP1 iv)** — never mutate/delete; append a
  superseding event carrying actor, timestamp, prior-value snapshot, reason. Full
  forensic trail; a revert can itself be reverted by appending again; aligns with
  "append-only/idempotent, no existence leak" and "non-success rows remain
  forensic-only … governed by … audit"
  (`…FORK_B_20260627.md:19-22`; `plm-collab-remaining-todo-dev-verification-20260630.md:129-130`).

**Idempotency / no existence-leak** — mirror the batch-ack precedent (#898): only
rows currently `acknowledged` transition; already-`open` rows are no-ops; unknown
ids silently skipped (not 404); commit once; return only transitioned rows
(`ops_router.py:206-224`).

**Worker-stability caveat (load-bearing).** Any revert that touches
`child_obsoleted` without also replacing/un-expiring the effectivity is **not
stable** against the poller (`service.py:234-236`). A DP1 (iii) revert's audit
model MUST therefore define how it prevents worker re-promotion (e.g. the
correction event acting as a suppression marker the service consults) — this is why
(iii) is deferred.

**RECOMMENDED default (pending owner ratification):** adopt the **append-only
superseding correction event** as the audit model for all revert scopes, with
batch-ack idempotency semantics; do not destructively clear `acknowledged_*` —
preserve them as historical fact superseded by the correction event.

---

## 4. Reuse Map (IF ratified)

| Existing component | Reused for revert as… |
|---|---|
| `DateObsoleteImpact` model (`models/date_obsolete.py:32`) | Target entity; `state`/`acknowledged_*` are the review-axis fields a (i)/(ii) revert addresses. May need additive columns or a sibling correction-event table (DP3). |
| `_IMPACT_STATES` (`ops_router.py:30`) | `'open'` is already a member, so a reopen target needs no new state; any new intermediate state would require updating this set AND the summary `by_state` contract (`ops_router.py:140`). |
| `_impact` serializer (`ops_router.py:47`) | Response shape for revert endpoints, unchanged. |
| `_impact_query` (`ops_router.py:71-85`) | **Read-only helper behind list/summary/export — revert must NOT write through it**; it stays the safe triage surface. |
| `require_admin_permission` (`auth.py:310-324`) | Baseline authz gate (DP2); superuser tightening for (iii). |
| Batch-acknowledge path (#898, `ops_router.py:192-224`) | Structural template for a `revert-batch`: de-dup preserving order, one IN query, transition only matching rows, single commit, return only transitioned rows. |
| Single-acknowledge path (`ops_router.py:243-260`) | Structural template for a single `.../{impact_id}/revert` route. |
| Worker / `DateEffectivityObsoleteService` | Only relevant for DP1 (iii); the worker itself is unchanged. A (iii) revert must reconcile with `_upsert_impact` re-scan and the reason-code taxonomy (`service.py:160-165,234-236`). |

Natural new routes (mirroring the two ack shapes): single
`POST /cadpdm/date-obsolete-impacts/{impact_id}/revert` and bulk
`POST /cadpdm/date-obsolete-impacts/revert-batch`.

---

## 5. Invariants Preserved

- **Default-off worker, two required gates** — global `DATE_EFFECTIVITY_OBSOLETE_ENABLED`
  (default false) AND per-tenant `cadpdm_date_obsolete` (`WIRING_20260618.md:9,18-22`).
- **Admin-gated ops writes, idempotent, no existence leak, never re-trigger
  obsolete** (`FORK_B_20260627.md:19-27`; `WIRING_20260618.md:23-25`).
- **Read-only forensic/export surfaces stay read-only** — list/summary/export reuse
  `_impact_query` and never write (`ops_router.py:157-159`).
- **Superuser-only forensic surfaces stay superuser-only**
  (`plm-collab-remaining-todo-dev-verification-20260630.md:28-29`).
- **Per-phase opt-in before code** — gating is deliberate, not leftover
  (`…gated-development-order-…:102,123`).
- **No silent mutation of worker-derived state** — the `child_obsoleted` axis and
  the Item `Obsolete` lifecycle are not touched by a (i)/(ii) revert; a (iii) revert
  requires its own ratification and a defined worker-re-promotion guard.

---

## 6. Proposed Implementation Phases (design-only, IF ratified)

Each phase follows the grounded → build → verify → CI cadence. **None starts
before owner ratification of DP1–DP3.**

**Phase R0 — Ratification (this doc).** Owner selects DP1 scope, DP2 authz tier,
DP3 audit model. No code. Gate: written owner sign-off.

**Phase R1 — Review-flag revert (DP1 (i)/(ii), append-only audit).** Scope:
`acknowledged → open` reversal on `DateObsoleteImpact` only, via the ratified audit
mechanism. No Item lifecycle, no worker change. Build: single + batch revert routes
mirroring the ack shapes; reuse `require_admin_permission`, `_impact` serializer,
batch-ack idempotency; add audit persistence per DP3. *Verify:* forward-then-revert
round trips, idempotency (already-`open`/unknown-id skipped, not 404), no existence
leak, `_impact_query`/export remain read-only, revert does NOT re-trigger the
worker, and the `_IMPACT_STATES`/`by_state` summary contract test updated if any
state is added. *CI:* green alongside existing date-obsolete tests.

**Phase R2 — Undo child-obsolete promotion (DP1 (iii)) — SEPARATE later
ratification.** Prerequisite grounding: resolve whether `LifecycleService.promote`
is reversible with recoverable prior-state audit; resolve the `child_obsoleted=True`
ambiguity so only rows the worker actually promoted are targeted; define the worker
re-promotion suppression guard. Build: superuser-gated revert restricted to
`reason='child_obsoleted'` rows promoted this run; reverse via the lifecycle
service's own reversal path (never a direct state poke); register the suppression
marker. *Verify:* no over-revert of already-`Obsolete` Items; worker-tick stability;
`child_obsolete_failed`/`child_effectivity_expired`/`bom_line_effectivity_expired`
rows excluded. *CI:* green; requires its own ratification before start.

---

## 7. NOT Decided Here / Awaiting Owner Ratification

- **DP1** — which of the four meanings, and whether scopes compose. The docs
  enumerate the four but state **no** preferred default (`…gated-development-order-…:111`).
- **DP2** — the authorization tier (admin vs superuser vs new entitlement).
- **DP3** — the audit model (in-place vs revert columns vs append-only event) and
  whether it implies a schema/migration; whether a revert clears or preserves
  `acknowledged_*`.
- Whether Item-lifecycle undo (DP1 (iii)) is in scope at all, given it reverses
  worker-derived lifecycle state and needs a worker-re-promotion guard.

---

## 8. Open Questions

- **Is `LifecycleService.promote(item, 'Obsolete')` reversible, and does it write
  audit/history recovering the Item's PRIOR lifecycle state?** Lives in
  `yuantus.meta_engine.lifecycle.service`, outside the date_obsolete files; bears
  directly on a (iii) revert's blast radius — not inspected here.
- **Does reverting require re-opening / extending the effectivity `end_date`?** How
  the effectivity's own expired state relates to a stable revert (vs the poller
  re-expiring it) is not covered by these files.
- **Do any consumers outside this feature read `meta_date_obsolete_impacts` or the
  Item's `Obsolete` state** (downstream BOM / publication logic) such that a revert
  must notify them?
- **Actor split for audit:** the promotion actor is the system user (not stored on
  the row), while the ack actor is stored in `acknowledged_by_id` (nullable FK, ON
  DELETE SET NULL, `date_obsolete.py:51-53`). A revert-audit model must decide how it
  records "who reverted" for both axes.

---

## 9. References

- Revert-semantics enumeration + governance gate: `plm-collab-remaining-gated-development-order-and-verification-20260630.md` (`:41`, `:111`).
- Revert deferral + rationale: `plm-collab-remaining-todo-dev-verification-20260630.md` (`:114`, `:27-29`, `:129-130`).
- Prior slice that deferred revert: `DEV_AND_VERIFICATION_DATE_OBSOLETE_IMPACTS_FORK_B_20260627.md` (`:15-22`).
- Mechanism + wiring (default-off, two gates, flag-only depth-1): `DEV_AND_VERIFICATION_CADPDM_C3_DATE_OBSOLETE_MECHANISM_20260618.md`, `…_WIRING_20260618.md`.
- Sibling decision doc (locked-BOM ECO revision route): `plm-collab-phase7-locked-bom-eco-revision-route-design-20260630.md` (`#931`).
