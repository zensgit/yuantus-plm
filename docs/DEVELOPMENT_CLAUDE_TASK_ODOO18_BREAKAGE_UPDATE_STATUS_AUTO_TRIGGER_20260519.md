# Claude Taskbook: Odoo18 Breakage `update_status` Auto-Trigger

Date: 2026-05-19

Type: **Doc-only taskbook.** Changes no runtime, no schema, no
service. Specifies the contract a later, separately opted-in
implementation PR will deliver. Merging this taskbook does NOT
authorize that code.

## 1. Purpose

Tier-B #3 §3.3 (per the remainder catalog ratified at PR #601
`7fce255`). Add a **default-OFF** opt-in so a
`BreakageIncidentService.update_status(...)` transition to an
eligible status (`resolved` / `closed`) can automatically spawn
(or reuse) the design-loopback ECO via the §3.2 durable path.

This is the first slice that makes a *state transition* trigger
a side effect. Even default-OFF it changes runtime structure, so
the taskbook must pin: the trigger point, the switch name, the
transaction boundary, repeat-trigger semantics, error handling,
and — the central issue — how the auto-trigger composes with
§3.2's CAS-loss `session.rollback()` when both share the
status-change transaction.

Prerequisite: §3.2 durable idempotency (merged `2609bba` /
PR #604) — the auto-trigger reuses
`create_breakage_design_loopback_eco`'s durable
compare-and-swap, so repeated/concurrent triggers are
idempotent rather than duplicate-producing.

## 2. Current Reality (grounded — direct file reads)

All citations verified by direct read (per
[[feedback-verify-grounding-facts]]).

### `update_status` today

`src/yuantus/meta_engine/services/parallel_tasks_service.py`
`BreakageIncidentService.update_status` (line 4195):

```python
def update_status(self, incident_id: str, *, status: str) -> BreakageIncident:
    incident = self.session.get(BreakageIncident, incident_id)
    if not incident:
        raise ValueError(f"Breakage incident not found: {incident_id}")
    incident.status = status.strip().lower()
    incident.updated_at = _utcnow()
    self.session.flush()
    return incident
```

- **No transition detection.** It does not read the prior
  status; it just sets the new one. There is no `from_state`.
- Flushes; does NOT commit (caller owns the boundary).

### The status route

`src/yuantus/meta_engine/web/parallel_tasks_breakage_router.py`
`update_breakage_status` (line ~835):

- `service.update_status(incident_id, status=payload.status)`
  then a single `db.commit()`.
- `except ValueError` → 404 `breakage_not_found`.
- `except Exception` → 400 `breakage_status_invalid` (rollback).
- `BreakageStatusUpdateRequest` (line 88) is `{status: str}`.
- One commit at the end — the unit of atomicity is the whole
  handler.

### The thing being auto-invoked (§3.2)

`create_breakage_design_loopback_eco(incident_id, *, user_id,
allow_duplicate=False)` (line ~4275, merged `2609bba`):

- prepares → raises `ValueError` if status ∉
  `eligible_statuses`;
- durable dedupe via `incident.eco_id` + the CAS UPDATE;
- **CAS-loser path calls `self.session.rollback()`** (full
  transaction rollback — undoes its own `ECOService.create_eco`
  INSERT) then re-reads and returns `created=False` with the
  winner ECO;
- caller owns commit.

### Eligibility gate

`breakage_eco_closeout_contract.py`:
`eligible_statuses = frozenset({"resolved", "closed"})` (line
40); `is_breakage_eligible_for_design_loopback` returns
`descriptor.status in eligible_statuses` (line 113). Open /
in_progress / unknown are NOT eligible.

## 3. Design decisions

### 3.A Trigger point — PRE-RATIFIED: fire on eligible new status (no delta detection)

`update_status` has no prior-status read. Two readings:

- **A1 (recommended, pre-ratified):** when `auto_loopback=True`,
  after the status flush, fire the loopback iff the **new**
  status is eligible (`is_breakage_eligible_for_design_loopback`
  on the post-update descriptor). No old-vs-new delta. §3.2's
  durable idempotency makes a redundant fire safe (a
  `resolved → resolved` no-op update just returns
  `created=False`).
- **A2:** add prior-status read and fire only on an actual
  transition into an eligible status.

Author pre-ratifies **A1**: A2 adds a prior-status read +
delta logic for zero behavioral benefit (the eligibility
predicate already restricts to `{resolved, closed}` and §3.2
de-dupes redundant fires). Reviewer can flag A2 if an
explicit "only on transition" audit signal is wanted — but
that belongs to §3.6 (event emission), not the trigger
mechanism.

### 3.B Switch name + signature — PRE-RATIFIED (per #601 §3.3)

```python
def update_status(
    self,
    incident_id: str,
    *,
    status: str,
    auto_loopback: bool = False,
    loopback_user_id: Optional[int] = None,
) -> BreakageIncident:
```

- `auto_loopback` defaults `False` — **default-OFF preserves
  byte-identical pre-R1 behavior** (no eligibility check, no
  create call, no extra query, no `eco_id` write). Pinned by a
  MANDATORY test.
- `loopback_user_id` is the actor passed to
  `create_breakage_design_loopback_eco(..., user_id=...)`. The
  route maps `int(user.id) → loopback_user_id`.
- `BreakageStatusUpdateRequest` gains
  `auto_loopback: bool = False`.

### 3.C Transaction boundary + the §3.2-rollback composition — OPEN, reviewer ratify

The route owns the single `db.commit()`. With
`auto_loopback=True`, `update_status` flushes the status change
and then calls `create_breakage_design_loopback_eco` **in the
same session/transaction**. The route's one commit then commits
both the status change and the loopback link atomically.

**The hard interaction:** §3.2's `create_breakage_design_loopback_eco`
CAS-loser path calls `self.session.rollback()` — a *full*
transaction rollback. Composed into `update_status`, a CAS loss
(genuine concurrency: two callers simultaneously do
`update_status(resolved, auto_loopback=True)` on the SAME
incident) would roll back the **status change too**, because it
shares the transaction. The caller would get `created=False`
with the winner ECO but the status update silently lost.

Options:

- **C1 (author recommendation):** Accept and *document* the
  rare-race retry semantic. The CAS-loss only happens under two
  simultaneous resolve-with-auto-loopback calls on the *same*
  incident. The implementation detects the lost status change
  (the service re-applies the status after the §3.2 method
  returns `created=False`, OR the route surfaces a retryable
  **409 `breakage_loopback_link_race`**). On retry the incident
  is already linked, so `create_…eco` returns `created=False`
  fast and the status re-applies cleanly. Transient,
  self-healing, no change to merged §3.2. The taskbook pins
  the route mapping + a MANDATORY test simulating the race.
- **C2:** Wrap the auto-triggered `create_…eco` in a SAVEPOINT
  (`session.begin_nested()`) so a CAS-loss only unwinds the
  loopback attempt, not the status flush. **Blocked:** §3.2's
  loser path calls `self.session.rollback()` (full rollback),
  which unwinds the whole transaction *including* the
  savepoint — so a savepoint wrapper does NOT contain it
  without changing merged §3.2. Out of §3.3 scope.
- **C3:** Two-phase — commit the status change first, then a
  second transaction for the loopback. Breaks the route's
  single-commit shape and "caller owns the boundary"; rejected.

**Author recommends C1**, with the §3.3 service method
re-applying the status write after a `created=False`-with-prior-
rollback (detected because the post-call session no longer has
the flushed status), and the route mapping an unrecoverable race
to a retryable 409. Reviewer must ratify C1 vs. mandating a
§3.2 refactor (a separate opt-in) to make C2 viable. **This is
the central open question of this taskbook.**

### 3.D Repeat-trigger semantics — PRE-RATIFIED (via §3.2)

Repeated `update_status(resolved, auto_loopback=True)` on an
already-linked incident: `create_…eco`'s durable `eco_id`
lookup returns the existing ECO, `created=False`, **no
duplicate**. This is exactly §3.2's durable idempotency; §3.3
adds no new dedupe logic. The §3.2↔§3.3 relationship is: §3.3
is a *trigger*, §3.2 is the *idempotent effect*.

### 3.E Error handling — PRE-RATIFIED

- **Incident not found** → `ValueError("Breakage incident not
  found: …")` (existing) → route 404 `breakage_not_found`
  (unchanged).
- **New status ineligible** (e.g. `in_progress`) +
  `auto_loopback=True` → the status change proceeds normally
  and the loopback is **skipped** (gate on
  `is_breakage_eligible_for_design_loopback` BEFORE calling
  `create_…eco`; do NOT call it and swallow a `ValueError`).
  `auto_loopback` on a non-eligible transition is a valid
  no-op.
- **Eligible + `create_…eco` raises** (e.g. `ECOService.create_eco`
  permission failure) → propagate; the whole transaction rolls
  back (status change too). This is **intended atomic
  coupling**: opting into `auto_loopback` means accepting that
  an ECO-create failure blocks the status change. The route
  surfaces the ECO error verbatim (consistent with §3.1's
  pattern — no breakage-route-local re-mapping).
- **CAS race loss** → §3.C C1.

### 3.F Relationship to §3.2 `created=False`

The auto-trigger's outcome is reported via the same
`BreakageDesignLoopbackEcoCreation.created` boolean §3.1/§3.2
already expose. `update_status(auto_loopback=True)` does NOT
change its own return type (still returns the `BreakageIncident`)
— the loopback result is a side effect. If callers need the
loopback outcome, that is a §3.6 (event) / future-return-shape
concern, explicitly out of §3.3 scope.

## 4. R1 Target Output (for the impl PR)

- `parallel_tasks_service.py`: `update_status` gains
  `auto_loopback` + `loopback_user_id` kwargs; when
  `auto_loopback` and the post-flush incident is eligible, call
  `create_breakage_design_loopback_eco(incident_id,
  user_id=loopback_user_id, allow_duplicate=False)`; implement
  the §3.C-C1 status-re-apply on the rare CAS-loss path.
- `parallel_tasks_breakage_router.py`:
  `BreakageStatusUpdateRequest` gains `auto_loopback: bool =
  False`; the route passes `auto_loopback=payload.auto_loopback,
  loopback_user_id=int(user.id)`; maps an unrecoverable
  CAS-race to **409 `breakage_loopback_link_race`** (retryable);
  ECO permission failure propagates verbatim (rollback +
  re-raise, mirroring §3.1).
- No new route; `len(app.routes)` stays 677.
- No edit to `create_breakage_design_loopback_eco` or merged
  contracts or §3.2's CAS/rollback.

## 5. Tests Required (in the impl PR)

MANDATORY exactly-named:

- **`test_update_status_default_off_is_byte_identical`** — with
  `auto_loopback` absent/False: no eligibility check, no
  `create_…eco` call (spy asserts not called), no `eco_id`
  write, status+updated_at behave exactly as pre-§3.3.
- **`test_update_status_auto_loopback_on_eligible_status_spawns_link`** —
  `auto_loopback=True`, status→`resolved`: incident gets
  `eco_id` linked, the loopback ECO exists, one commit.
- **`test_update_status_auto_loopback_skips_ineligible_status`** —
  `auto_loopback=True`, status→`in_progress`: status changes,
  `create_…eco` NOT called (spy), no ECO, no `eco_id`.
- **`test_update_status_auto_loopback_repeat_is_idempotent`** —
  two sequential `update_status(resolved, auto_loopback=True)`:
  second returns the same ECO via §3.2 durable dedupe; exactly
  one ECO; status stable.
- **`test_update_status_auto_loopback_cas_race_is_retryable`** —
  simulate the §3.C-C1 concurrent-link race (two sessions on a
  shared engine, mirroring §3.2's CAS test): the loser's
  status change is recoverable (re-applied by the service OR
  surfaced as 409 `breakage_loopback_link_race`), and a retry
  succeeds with the incident already linked (`created=False`)
  and the status applied. Pins whichever §3.C resolution the
  reviewer ratifies.
- **`test_update_status_auto_loopback_eco_permission_failure_rolls_back_status`** —
  eligible + `ECOService.create_eco` permission error:
  whole transaction rolls back (status NOT changed), error
  propagates verbatim. Pins the §3.E atomic-coupling decision.

Plus: route-level tests (auto_loopback default False; 409 race
mapping; ECO-permission propagation), and the existing
breakage/route/phase-4(677)/doc-index/R2-portfolio regression
stays green.

## 6. Verification Commands (impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_breakage_update_status_auto_trigger.py \
  src/yuantus/meta_engine/tests/test_breakage_design_loopback_durable_idempotency.py \
  src/yuantus/meta_engine/tests/test_breakage_design_loopback_eco_creation_wiring.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_breakage_design_loopback_route.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_breakage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_odoo18_r2_portfolio_contract.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/parallel_tasks_service.py \
  src/yuantus/meta_engine/web/parallel_tasks_breakage_router.py
git diff --check
```

No alembic / tenant-baseline — §3.3 adds no schema (§3.2's
`eco_id` is the durable substrate; §3.3 only triggers it).

## 7. DEV/verification MD requirements (impl PR)

`docs/DEV_AND_VERIFICATION_ODOO18_BREAKAGE_UPDATE_STATUS_AUTO_TRIGGER_R1_20260519.md`
+ index line. Must document: ratified §3.A trigger reading;
§3.C resolution chosen + why (and the §3.2-rollback composition
analysis); §3.E atomic-coupling decision; default-OFF
byte-identical proof; the §3.2↔§3.3 idempotency relationship;
inter-slice status (§3.4 now reuses §3.3's path; §3.6/§3.7
unchanged).

## 8. Non-Goals (hard boundaries for the impl PR)

- No edit to `create_breakage_design_loopback_eco`, §3.2's CAS
  or its `session.rollback()`, or any merged contract.
- No new route; no schema/alembic/tenant-baseline.
- No helpdesk-sync auto-trigger (that is §3.4, which will reuse
  §3.3's path through a different entrypoint — separate opt-in).
- No event emission (§3.6) / metrics (§3.7).
- No change to `update_status`'s return type.
- No default-ON. `auto_loopback` defaults False; flipping the
  default is a separate explicit opt-in.
- `.claude/` and `local-dev-env/` stay out of git.

## 9. Decision Gate / Handoff

Doc-only. Implementation owned by Claude or the project owner
**only after this taskbook is merged AND a separate explicit
opt-in is given**, on branch
`feat/odoo18-breakage-update-status-auto-trigger-r1-20260519`.

Follow-ups (each its own opt-in): §3.4 helpdesk-sync
auto-trigger (reuses §3.3 path, different entrypoint); §3.6
event emission; §3.7 metrics; default-ON flip (if ever).

## 10. Reviewer Focus

- **§3.C is the central question.** Confirm C1 (document the
  rare-race retry + 409 mapping, status re-applied) vs.
  mandating a separate §3.2 refactor to enable C2 (savepoint).
  C1 keeps §3.3 minimal and doesn't touch merged §3.2; the
  race is two simultaneous resolve+auto_loopback calls on one
  incident, transient, self-healing on retry. Push back if the
  atomic status+loopback guarantee under concurrency must be
  stronger than "retryable 409".
- **§3.A** trigger reading: A1 (fire on eligible new status, no
  delta) vs. A2 (transition delta). Author recommends A1.
- **§3.E** atomic coupling: confirm that opting into
  `auto_loopback` correctly means an ECO-create permission
  failure rolls back the status change (intended) vs. a
  best-effort "status changes anyway, loopback failure
  swallowed" alternative (rejected — silent loopback loss).
- Confirm default-OFF must be byte-identical (no extra query /
  no eligibility check on the False path) and is test-pinned.
- **Route exception-handling refinement (cross-callsite
  subtlety).** The existing status route catches generic
  `except Exception` → **400 `breakage_status_invalid`** +
  rollback. As-is, that block would mask both (a) an
  `ECOService.create_eco` permission failure and (b) the §3.C
  retryable race as a generic 400. The impl PR must refine the
  status route so the §3.E ECO error propagates verbatim
  (mirroring §3.1's explicit `except Exception: rollback;
  raise`) and the §3.C race surfaces as the retryable 409
  `breakage_loopback_link_race` — NOT collapsed into the
  pre-existing 400. Confirm the impl PR pins this with a
  route-level test; a silent 400 here would make a transient
  race indistinguishable from a real invalid-status error.
- Did anything pre-decide a §3.4+ slice or touch merged §3.2?
  It must not.
