# Claude Taskbook: Odoo18 Breakage Design-Loopback Event Emission

Date: 2026-05-19

Type: **Doc-only taskbook.** Changes no runtime, no schema, no
service. Specifies the contract a later, separately opted-in
implementation PR will deliver. Merging this taskbook does NOT
authorize that code.

## 1. Purpose

Tier-B #3 §3.6 (per the remainder catalog ratified at PR #601
`7fce255`). Emit a domain event when the design-loopback ECO
result converges, so downstream consumers can react — **reusing
the existing transactional EventBus / `enqueue_event` / ECO
event pattern, adding NO new event infrastructure and NO
subscriber**. §3.6 is emission-only.

The single non-obvious risk this taskbook must pin: the event
must dedup correctly under the §3.2 CAS-loser
`self.session.rollback()` (no double-emit on the race), the
emission-failure semantics must be unambiguous, and the
default-OFF / merged-signature questions must be ratified
before any code.

Prerequisites (merged): §3.1 route (`a02dbd0`), §3.2 durable
idempotency (`2609bba`), §3.3 `update_status` auto-trigger
(`757c411`), §3.4 helpdesk-sync auto-trigger (`fb3f099`). §3.6
reuses the shared `_auto_trigger_design_loopback` helper and
`create_breakage_design_loopback_eco`.

## 2. Current Reality (grounded — direct file reads)

All citations verified by direct read (per
[[feedback-verify-grounding-facts]]). Line numbers vs `main` @
`fb3f099`.

### The transactional outbox (the mechanism §3.6 reuses)

`src/yuantus/meta_engine/events/transactional.py`:

- `enqueue_event(session, domain_event)` appends to
  `session.info["meta_engine_pending_events"]`.
- Session hooks: **`after_commit` → publish all pending via the
  in-memory `event_bus`**; **`after_soft_rollback` → DROP the
  pending queue** (line 54-56).
- ⇒ enqueue is **transactional**: ANY rollback (including the
  §3.2 CAS-loser `self.session.rollback()`) discards queued
  events; publish happens only after a successful commit.

`src/yuantus/meta_engine/events/event_bus.py`:
`EventBus.publish` is an in-memory singleton; each handler is
wrapped in `try/except` that **logs and continues** (a handler
failure never propagates, never rolls back). Publish runs in
`after_commit` — *after* the DB transaction is already
committed.

`src/yuantus/meta_engine/events/domain_events.py`: `DomainEvent`
is a Pydantic `BaseModel` with `event_id` (uuid default),
`event_type: str`, `actor_id: Optional[int]`. `EcoCreatedEvent`
(`event_type="eco.created"`, `eco_id/eco_type/state/product_id`)
is the shape to mirror.

### The ECO event pattern (the precedent to mirror)

`eco_service.py`: `_enqueue_eco_created(self, eco)` (line 75)
calls `enqueue_event(self.session, EcoCreatedEvent(...))`.
`create_eco` (line 504): `check_permission` (520, raises
**before** any add/flush) → `session.add` (534) → `flush`
(535) → **`self._enqueue_eco_created(eco)` (550)** → `return`
(551). So `EcoCreatedEvent` is enqueued **before**
`create_breakage_design_loopback_eco`'s CAS. On the §3.2
CAS-loser, `create_breakage_design_loopback_eco`'s
`self.session.rollback()` drops that `EcoCreatedEvent` (and the
loser's ECO INSERT); the winner's session commits and publishes
its own. **`EcoCreatedEvent` already dedups on the CAS-loser
via rollback-drop — §3.6 reuses this exact mechanism.**

### The loopback funnel + the three trigger sources

`create_breakage_design_loopback_eco` (line 4382) currently
enqueues **no** breakage event. Its branches:

- **dedupe early-return** → `created=False`, an existing ECO
  (no `create_eco`, no CAS, **no rollback**);
- **CAS winner** (`result.rowcount == 1`, after the post-CAS
  flush) → `created=True`;
- **CAS-loser** (`rowcount == 0`) → `self.session.rollback()`
  → re-read → `created=False`, winner ECO (or `eco=None`
  unrecoverable).

All three trigger sources funnel through this one method:

- **§3.1 route** `create_breakage_design_loopback_eco` (router)
  → `service.create_breakage_design_loopback_eco(...)`
  directly;
- **§3.3** `update_status` → `_auto_trigger_design_loopback`
  (the shared helper, `757c411`) → `create_breakage_design_loopback_eco`;
- **§3.4** `apply_helpdesk_ticket_update` →
  `_auto_trigger_design_loopback` → `create_breakage_design_loopback_eco`.

The §3.3/§3.4 helper self-heal re-applies **only the incident
status** after a CAS-loser rollback; it does NOT call
`create_breakage_design_loopback_eco` again — so the loopback
result is determined exactly once, inside
`create_breakage_design_loopback_eco`.

## 3. Design decisions

### 3.A Event class + payload — PRE-RATIFIED

New `BreakageDesignLoopbackEcoEvent(DomainEvent)` in
`domain_events.py` (mirrors `EcoCreatedEvent`):

```
event_type: str = "breakage.design_loopback_eco"
incident_id: str
eco_id: Optional[str]          # None only on the unrecoverable arm
created: bool                  # True=CAS winner created; False=reuse
trigger_source: str            # "route" | "update_status" | "helpdesk_sync"
incident_status: str           # the converged incident status
sync_status: Optional[str] = None        # helpdesk_sync source only
provider_ticket_status: Optional[str] = None  # helpdesk_sync source only
# actor_id (DomainEvent base) = the loopback actor (user_id)
```

A private `_enqueue_breakage_design_loopback_event(...)` mirrors
`_enqueue_eco_created` (one `enqueue_event(self.session, …)`).

### 3.B Emission point — DERIVED (not a free choice)

Emit **inside `create_breakage_design_loopback_eco`**, at the
two result-determination branches, mirroring exactly where
`ECOService.create_eco` enqueues `EcoCreatedEvent`:

- inside `if result.rowcount == 1:` (after the post-CAS flush,
  before the `created=True` return) — the **CAS winner**;
- inside the **dedupe early-return** branch (no `create_eco`,
  no `EcoCreatedEvent` here, but a legitimate "reuse" signal)
  — `created=False`;
- **NOT** inside the `rowcount == 0` CAS-loser branch.

This is a *derivation*, not an option: all three trigger
sources funnel through this one method, so one emission point
covers them with zero duplication; and the transactional outbox
makes the CAS-loser dedup automatic (see §3.C). A
per-call-site / per-helper emission alternative is **rejected**:
it double-emits on the race (winner + loser) and duplicates the
logic across the route, the helper, and two callers.

### 3.C CAS-loser dedup + "after convergence" — RATIFIED

**Two-stage timing.** `enqueue` happens at the
loopback-result-determination point (inside
`create_breakage_design_loopback_eco`); **`publish` happens at
`after_commit`**, by which time the whole request has converged
(status applied, ECO linked, and for §3.4 the helpdesk
mutations applied via the §3.C-β reorder). So "emit after the
create/reuse result converges" is satisfied *at publish time*
— enqueue-before-self-heal does NOT violate it.

**Dedup (the central pin).** Net guarantee: **exactly one
`BreakageDesignLoopbackEcoEvent` per incident-link resolution;
zero double-emit on the race** — by reusing the existing
rollback-drop, identical to `EcoCreatedEvent`:

- **CAS winner** → enqueue `created=True`; the route's single
  `db.commit()` → `after_commit` publishes once.
- **dedupe early-return** → enqueue `created=False` (reuse); no
  rollback on this path; publishes once on commit.
- **CAS-loser** → **enqueue NOTHING.** The winner already
  emitted `created=True` for this incident-link; the loser's
  own `self.session.rollback()` would drop a queued event
  anyway — explicit non-emission documents the intent and is
  robust to future reordering. (The loser request still
  succeeds at the route via the §3.3/§3.4 status self-heal;
  it simply contributes no event.)
- **unrecoverable arm** (`eco=None` →
  `BreakageDesignLoopbackLinkRace`) → the helper raises; the
  route rolls back; **zero events** (drop).

### 3.D Emission-failure strategy — RATIFIED (inherited, documented)

`enqueue_event` cannot fail (list append). `event_bus.publish`
runs **post-commit** and **swallows handler exceptions** (logs,
continues). Therefore:

- a subscriber/handler failure **never** rolls back the
  loopback or the status and **never** reaches the caller;
- emission is **best-effort, at-most-once, after-commit** —
  identical to every existing ECO/item event.

This is **intentional inheritance** of the existing
transactional-outbox behavior (same framing as the §3.3/§3.1
`PLMException` inheritance — documented, NOT re-litigated).
Delivery guarantees / durable outbox / retry are explicitly
**scoped out** (a separate future opt-in). There is NO
"emission failure rolls back the loopback" — publish is
post-commit and structurally cannot.

### 3.E Default-OFF switch — *the central question* (RATIFY ONE)

Existing ECO/item events emit **unconditionally**
(`EcoCreatedEvent` has no opt-in). The prior §3.3/§3.4
discipline used a default-OFF opt-in. Three options — the impl
PR cannot ship until ONE is ratified:

- **(S1) Per-call param** — `emit_loopback_event: bool = False`
  on `create_breakage_design_loopback_eco` + the helper, plus
  `emit_loopback_event` on the 3 request models. Strictest
  byte-identical-when-off; widest API surface (3 request
  models touched).
- **(S2) Settings flag** — e.g.
  `settings.breakage_design_loopback_events_enabled` (default
  `False`); the emit helper is a no-op unless enabled. Smallest
  API blast-radius, one deploy-time switch, default-OFF
  preserved. **Author-recommended.**
- **(S3) No switch** — emit unconditionally, mirroring the
  `EcoCreatedEvent` precedent; relies on
  *no-subscribers-by-default* for inertness (the EventBus has
  no subscribers until a future consumer opt-in subscribes).
  Most consistent with the existing event pattern; weakest
  "byte-identical OFF" story.

Author recommends **S2** (smallest surface, true default-OFF,
one flip when a consumer is ever added). Reviewer ratifies one.
This subsection + §3.F are the gate; the §3.B emission point is
settled by the outbox.

### 3.F Merged-signature additive authorization — RATIFIED

Threading `trigger_source` (and, if S1, `emit_loopback_event`)
requires additive kwargs on the already-merged
`create_breakage_design_loopback_eco` and the
`_auto_trigger_design_loopback` helper. §3.4's §8 said "no edit
to `create_breakage_design_loopback_eco`." **§3.6 explicitly
authorizes additive, non-semantic keyword parameters with
defaults that preserve every existing caller's behavior
byte-for-byte** — no CAS / `session.rollback()` / contract
change (same allowance framing as §3.4's §3.E
helper-extraction). Threading:

- `create_breakage_design_loopback_eco(..., trigger_source:
  str = "route")` — default keeps the §3.1 direct route caller
  unchanged.
- `_auto_trigger_design_loopback(..., trigger_source: str)` —
  **required, no default** (forces the helper-using call sites
  to name it; cannot be silently forgotten). `update_status`
  passes `"update_status"`; `apply_helpdesk_ticket_update`
  passes `"helpdesk_sync"`.

Canonical `trigger_source` values: **`"route"` |
`"update_status"` | `"helpdesk_sync"`** (named here so the
impl PR does not bikeshed).

### 3.G No new route / schema / metrics / subscriber — PRE-RATIFIED

§3.6 only EMITS. No route, no Pydantic response change (unless
S1 adds the request-model opt-in field — that is the only
permitted request-model touch and only under S1), no schema /
alembic / migration, no metrics (that is §3.7 — untouched), no
subscriber/handler (consumers are each a separate future
opt-in). `execute_helpdesk_sync` / `record_helpdesk_sync_result`
remain non-trigger-points and unmodified.

## 4. R1 Target Output (for the impl PR)

- `domain_events.py`: add `BreakageDesignLoopbackEcoEvent`
  (§3.A).
- `parallel_tasks_service.py`: add
  `_enqueue_breakage_design_loopback_event`; enqueue at the
  §3.B CAS-winner + dedupe-early-return branches only (NOT the
  CAS-loser); add the §3.F additive `trigger_source` (+
  `emit_loopback_event` iff S1) kwargs to
  `create_breakage_design_loopback_eco` and
  `_auto_trigger_design_loopback`; `update_status` /
  `apply_helpdesk_ticket_update` pass their `trigger_source`.
- Switch wiring per the ratified S1/S2/S3.
- `parallel_tasks_breakage_router.py`: only if S1 — add
  `emit_loopback_event` to the 3 request models + pass-through;
  otherwise the routers are **unchanged**. No new route;
  `len(app.routes)` stays 677.
- No edit to §3.2's CAS / `session.rollback()`, the merged
  contracts, or `test_breakage_update_status_auto_trigger.py` /
  `test_breakage_helpdesk_sync_auto_trigger.py` beyond what new
  emission assertions require (those two stay green; see §5).

## 5. Tests Required (in the impl PR)

MANDATORY exactly-named (new file
`test_breakage_design_loopback_event_emission.py`). All tests
subscribe a capture handler via a **fixture that removes it on
teardown** — `event_bus` is a process-global singleton, so
subscriber isolation is mandatory or the suite is flaky:

- **`test_cas_winner_emits_one_event_with_created_true`** —
  one event; `created=True`; payload fields populated.
- **`test_dedupe_reuse_emits_one_event_with_created_false`** —
  durable-dedupe path; one event; `created=False`.
- **`test_cas_loser_race_emits_zero_events_winner_emits_one`**
  — the centerpiece. Two-session shared-engine race (mirroring
  §3.2/§3.4): the winner publishes exactly one `created=True`
  event; the loser publishes **zero**.
- **`test_unrecoverable_race_emits_zero_events`** — forced
  unrecoverable → `BreakageDesignLoopbackLinkRace` → rollback
  → zero events.
- **`test_eco_permission_failure_emits_zero_events`** —
  `ECOService.create_eco` denies before `_enqueue_eco_created`
  → rollback → zero events.
- **`test_idempotent_replay_emits_zero_events`** — §3.4 replay
  short-circuit returns before `create_…eco` → zero events.
- **`test_default_off_emits_zero_events`** (S1/S2) **or**
  `test_no_subscribers_is_byte_identical` (S3) — whichever
  switch is ratified.
- **`test_trigger_source_threaded_route_update_status_helpdesk`**
  — the three sources tag `trigger_source` correctly
  (parametrized or 3 mini-tests).

Plus: `test_breakage_update_status_auto_trigger.py` and
`test_breakage_helpdesk_sync_auto_trigger.py` stay green
(behavior unchanged when the switch is OFF), and the
breakage/route/phase-4(677)/doc-index/R2-portfolio regression.

## 6. Verification Commands (impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_breakage_design_loopback_event_emission.py \
  src/yuantus/meta_engine/tests/test_breakage_update_status_auto_trigger.py \
  src/yuantus/meta_engine/tests/test_breakage_helpdesk_sync_auto_trigger.py \
  src/yuantus/meta_engine/tests/test_breakage_design_loopback_durable_idempotency.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_breakage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_odoo18_r2_portfolio_contract.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/events/domain_events.py \
  src/yuantus/meta_engine/services/parallel_tasks_service.py \
  src/yuantus/meta_engine/web/parallel_tasks_breakage_router.py
git diff --check
```

The impl PR enumerates the exact event-infra regression files
it ran (the list above is indicative). No alembic /
tenant-baseline — §3.6 adds no schema.

## 7. DEV/verification MD requirements (impl PR)

`docs/DEV_AND_VERIFICATION_ODOO18_BREAKAGE_DESIGN_LOOPBACK_EVENT_EMISSION_R1_20260519.md`
+ index line. Must document: the ratified §3.E switch (S1/S2/S3)
**as implemented**; the §3.B single-funnel emission point with
the `EcoCreatedEvent`-mirroring rationale; the §3.C two-stage
timing + the CAS-loser zero-emit dedup proof; the §3.D
inherited best-effort-post-commit failure semantics (cross-ref
§3.3/§3.1, do not re-litigate); the §3.F additive-signature
authorization + canonical `trigger_source` values; the
event-bus test-isolation approach; inter-slice status (§3.7
metrics still untouched).

## 8. Non-Goals (hard boundaries for the impl PR)

- No new event infrastructure — reuse `enqueue_event` /
  `event_bus` / the `_enqueue_eco_created` pattern only.
- No subscriber / handler (consumers = separate future
  opt-ins, one each).
- No edit to §3.2's CAS / `session.rollback()`, any merged
  contract, or the merged behavior of
  `create_breakage_design_loopback_eco` (only additive,
  default-preserving kwargs per §3.F).
- No new route; no schema / alembic / tenant-baseline.
- No metrics (§3.7 — untouched). No event payload sourced from
  §3.7 aggregates.
- No delivery guarantee / durable outbox / retry (inherited
  best-effort; separate future opt-in).
- No default-ON (whichever switch — default OFF; flipping is a
  separate explicit opt-in).
- `execute_helpdesk_sync` / `record_helpdesk_sync_result` are
  NOT trigger points and are unmodified.
- `.claude/` and `local-dev-env/` stay out of git.

## 9. Decision Gate / Handoff

Doc-only. Implementation owned by Claude or the project owner
**only after this taskbook is merged AND a separate explicit
opt-in is given**, on branch
`feat/odoo18-breakage-design-loopback-event-emission-r1-20260519`.

Follow-ups (each its own opt-in): §3.7 metrics (taskbook then
impl); a concrete event consumer/subscriber; a durable-delivery
outbox; default-ON flip (if ever).

## 10. Reviewer Focus

- **§3.E is the central question — ratify ONE switch.** S1
  (per-call param, 3 request models) vs **S2 (settings flag,
  author-recommended, smallest blast-radius)** vs S3 (no
  switch, mirror `EcoCreatedEvent`, rely on
  no-subscribers-by-default). The §5 default-OFF test name
  follows the choice.
- **§3.F additive-signature authorization.** Confirm §3.6 may
  add default-preserving kwargs (`trigger_source`,
  optionally `emit_loopback_event`) to the merged
  `create_breakage_design_loopback_eco` / helper — additive,
  non-semantic, no CAS/rollback/contract change — and the
  required-on-helper / defaulted-on-`create_…eco` threading.
- **§3.B/§3.C dedup.** Confirm the single-funnel emission point
  + CAS-loser **zero-emit** (winner-only) is the correct
  no-double-emit semantic and that it reuses, not reinvents,
  the `EcoCreatedEvent` rollback-drop. Confirm the two-stage
  enqueue/publish timing satisfies "after convergence".
- **§3.D** confirm best-effort post-commit emission failure is
  acceptable inherited behavior (no loopback rollback on a
  publish/handler failure — structurally impossible
  post-commit) and that durable delivery is correctly scoped
  out.
- **Test isolation.** Confirm the event-bus subscriber
  teardown fixture requirement is pinned (global singleton →
  flaky without it).
- Did anything pre-decide §3.7, add a subscriber/route/schema,
  change §3.2's CAS, or touch a merged contract? It must not.
