# Claude Taskbook: Odoo18 Maintenance DB-Resolver Pure-Contract R1

Date: 2026-05-17

Type: **Doc-only taskbook.** Changes no runtime, no schema, no
service. Specifies the contract a later, separately opted-in
implementation PR will deliver. Merging this taskbook does NOT
authorize that code.

## 1. Purpose

R2 closeout §4 **Tier-A** follow-up #3b (companion to the merged
pack-and-go DB-resolver #588 `fdc1fd9` and follow-up #2 from the
merged maintenance↔workorder bridge #572 `ca6755f`). The merged
bridge contract
(`maintenance_workorder_bridge_contract.py`) consumes
`WorkcenterMaintenanceDescriptor`s the **caller** supplies, but
there is no typed, pure mapping from the persisted rows to those
descriptors. This R1 supplies that pure mapping — **the contract
still does not read the DB**; the caller fetches rows, the pure
function maps them. Mirrors the row→descriptor pattern just landed
in pack-and-go DB-resolver R1.

## 2. Current Reality (grounded — read before implementing)

- Merged `src/yuantus/meta_engine/services/maintenance_workorder_bridge_contract.py`:
  - `WorkcenterMaintenanceDescriptor` (frozen Pydantic v2,
    `extra="forbid"`):
    - `workcenter_id: str` (non-empty)
    - `equipment_id: str` (non-empty)
    - `equipment_status: str` (validated ∈ `EquipmentStatus` values)
    - `active_request_state: Optional[str] = None` (validated ∈
      `MaintenanceRequestState` values when non-null)
  - Blocking sets (lines 46–60):
    - `_BLOCKING_EQUIPMENT_STATUSES = {OUT_OF_SERVICE, DECOMMISSIONED}`
    - `_BLOCKING_REQUEST_STATES = {SUBMITTED, IN_PROGRESS}` —
      **`DRAFT` is deliberately non-blocking** (bridge contract
      lines 50–54: distinct from
      `MaintenanceService.get_maintenance_queue_summary` which
      counts `draft` into the active queue).
  - `_DEGRADED_EQUIPMENT_STATUS = IN_MAINTENANCE`.
  - `evaluate_workcenter_readiness` (pure) and
    `assert_workcenter_ready` (three machine-matchable failure
    prefixes: `workcenter_invalid:`/`workcenter_blocked:`/`workcenter_unknown:`)
    — **out of scope here**.
- Persisted source rows (file
  `src/yuantus/meta_engine/maintenance/models.py`):
  - `Equipment` — table `meta_maintenance_equipment` (line 97).
    Columns of interest:
    - `id: String, primary_key=True` (line 99).
    - `status: String(30), nullable=False, default=EquipmentStatus.OPERATIONAL.value`
      (lines 112–116).
    - `workcenter_id: String, nullable=True` (line 121) — **bare
      string column, NO FK constraint**. It is a soft link only;
      the resolver cannot rely on referential integrity, and an
      equipment row with `workcenter_id=None`/empty has no
      meaningful workcenter descriptor.
  - `MaintenanceRequest` — table `meta_maintenance_requests` (line
    153). Columns of interest:
    - `id: String, primary_key=True` (line 155).
    - `equipment_id: String, ForeignKey("meta_maintenance_equipment.id"), nullable=False, index=True`
      (lines 157–162).
    - `state: String(30), nullable=False, default=MaintenanceRequestState.DRAFT.value`
      (line 170).
    - `created_at: DateTime, server_default=now(), nullable=False`
      (line 189) — the natural sort key for "newest request".
  - `EquipmentStatus` enum (lines 37–41): exactly
    `{OPERATIONAL, IN_MAINTENANCE, OUT_OF_SERVICE, DECOMMISSIONED}`.
  - `MaintenanceRequestState` enum (lines 44–49): exactly
    `{DRAFT, SUBMITTED, IN_PROGRESS, DONE, CANCELLED}`.
- **No existing producer.** `WorkcenterMaintenanceDescriptor` is
  input-only in the merged bridge. There is no service method
  today that picks a single "active request state" for one
  equipment. The R1 resolver must therefore *define* the selection
  rule. Three in-tree precedents must be reconciled (§3 Policy A
  surfaces this for reviewer ratification):
  - `MaintenanceService.list_requests`
    (`src/yuantus/meta_engine/maintenance/service.py:241`):
    `q.order_by(MaintenanceRequest.created_at.desc()).all()` —
    pins **newest-first ordering**, but says nothing about which
    states count as "active."
  - `MaintenanceService.get_maintenance_queue_summary`
    (`src/yuantus/meta_engine/maintenance/service.py:372–376`):
    `active_states = {DRAFT, SUBMITTED, IN_PROGRESS}` — answers
    *"is there queued work?"*, **includes `DRAFT`**.
  - `MaintenanceService.get_preventive_schedule`
    (`src/yuantus/meta_engine/maintenance/service.py:313–317`):
    `active_states = {SUBMITTED, IN_PROGRESS}` — answers
    *"what's already in-flight?"*, **excludes `DRAFT`**.
  - The merged bridge contract's `_BLOCKING_REQUEST_STATES =
    {SUBMITTED, IN_PROGRESS}` (lines 55–60) — answers *"is the
    workcenter blocked right now?"*, also excludes `DRAFT`.
  In-tree code therefore has **two distinct active-state
  definitions** (queue-visibility vs. blocking/in-flight). The
  resolver's `active_request_state` feeds the bridge contract's
  blocking logic — so its selection rule directly shapes whether
  `DRAFT` is even *representable* in the descriptor stream the
  bridge consumes.
- **Equipment.workcenter_id FK hardening** is one of the bridge
  contract's three documented follow-ups (memory:
  maintenance-bridge `ca6755f`) — explicitly **NOT** in this R1's
  scope; an equipment row missing `workcenter_id` is a caller-side
  data state, not something the resolver fixes.

## 3. Row → Descriptor Boundary (the core of this taskbook)

The contract is **pure**: it does **not** query. The caller fetches
and passes typed row views; one descriptor is produced per
`(equipment_row, request_rows)` pair.

| Source rows | Resolver output |
|---|---|
| `equipment_row` with valid `workcenter_id` + 0 request rows | `equipment_status = equipment_row.status`, `active_request_state = None` |
| `equipment_row` + request rows with **any** non-terminal state | `active_request_state = ` the **first non-terminal state in input order** (caller orders, see §3 Policy A) |
| `equipment_row` + request rows where every state is terminal (`done`/`cancelled`) | `active_request_state = None` |

### Policies (some open for reviewer ratification)

**Policy A — Active-request selection (OPEN for reviewer
ratification, mirroring #587 §3 raise-on-mismatch pattern).**

The resolver must produce `active_request_state: Optional[str]` for
each equipment. There are three coherent options; in-tree code
contains precedents for the first two (see §2). The taskbook author
recommends **Option A2** but flags this as the reviewer's call:

- **Option A1 — surface non-terminal (DRAFT included).**
  Active states = `{DRAFT, SUBMITTED, IN_PROGRESS}` (mirrors
  `get_maintenance_queue_summary`). Resolver picks the **first
  non-terminal in input order**; terminal-only inputs → `None`.
  Pro: honestly surfaces "draft request exists" — distinct from
  "no request at all"; the bridge's blocking rule
  (`{SUBMITTED, IN_PROGRESS}`) correctly treats `DRAFT` as
  non-blocking, so it is safe to feed. Con: the resolver and the
  bridge use **different** definitions of "active", which the
  reviewer must verify is intentional.
- **Option A2 — surface blocking-relevant only (DRAFT excluded).**
  Active states = `{SUBMITTED, IN_PROGRESS}` (mirrors
  `get_preventive_schedule` and the bridge's
  `_BLOCKING_REQUEST_STATES`). Resolver picks the **first
  submitted/in_progress in input order**; everything else
  (including `DRAFT`) → `None`. Pro: resolver and bridge agree on
  the active-state definition; **no draft state is ever fed into
  `active_request_state` so the descriptor stream is internally
  consistent with the bridge's blocking semantics**. Con: loses the
  diagnostic "draft exists" signal — a downstream consumer cannot
  distinguish "no request" from "only-a-draft" from the descriptor
  alone.
- **Option A3 — return ALL states (no filter).** Pick the newest
  request in input order regardless of state; surface `done` /
  `cancelled` too. Pro: zero policy embedded in the resolver. Con:
  the bridge would receive `active_request_state=DONE` for
  long-completed work, which the bridge's validator rejects today
  (only `MaintenanceRequestState` *values* are accepted — `done`
  is valid by value-domain, but semantically the bridge expects
  "active") and which makes `active_request_state` non-discriminating
  for the bridge's blocking rule. **Not recommended.**

**Author recommendation: Option A2** — the resolver's purpose is to
build descriptors that feed `evaluate_workcenter_readiness`, whose
blocking logic ignores `DRAFT`. Aligning the resolver's active-set
with the bridge's `_BLOCKING_REQUEST_STATES` keeps the contract
internally consistent and prevents a future reader from wondering
why one side excludes `DRAFT` and the other includes it. The
"draft-exists" diagnostic, if needed later, belongs on a separate
descriptor field (a separate opt-in) — not on
`active_request_state`.

**Reviewer: confirm A1 vs A2 (vs A3 if you disagree with both)
before this taskbook is merged.** Whichever is chosen, the
selection key is the **first match in input order**; the caller is
responsible for ordering (typically `created_at DESC` to match
`MaintenanceService.list_requests`), and the resolver does not
re-sort internally.

**Policy B — Equipment-request id-mismatch raises (PRE-RATIFIED,
strict reading; deliberate carry-over from #588 case (b)).** If ANY
`request_row.equipment_id != equipment_row.id` in the input pair,
the resolver **raises `ValueError`** — caller bug. The rule is
unconditional on whether the mismatching row would have been the
chosen one. This pre-applies the strict reading reviewer-ratified
at merge time on PR #588 (case (b): "stray row when the link has
no pinned id" extension); not opening this again because the
ratification carried in #588 closed the question. This is
*input-shape validation*, **not** the bridge contract's enforcement
(which remains `assert_workcenter_ready`, untouched). If the
reviewer for this taskbook wants to roll back to the narrower
reading, flag it — but the default is the #588-consistent strict
reading.

**Policy C — Equipment.workcenter_id is a soft link
(documented, not RATIFIED).** Because `Equipment.workcenter_id` is
`nullable=True` with no FK, an equipment row with
`workcenter_id=None`/empty cannot be resolved to a
workcenter-scoped descriptor. The merged descriptor's existing
`_non_empty` validator on `workcenter_id` already raises in that
case; the resolver does not add a separate check. (This keeps the
FK-hardening question — the bridge's documented follow-up (c) —
out of this contract's scope.)

**Policy D — Equipment.status is non-Optional in the row DTO
(documented, not RATIFIED).** Because `Equipment.status` is
`nullable=False` with a default, every persisted row has a string
status; the row DTO mirrors this with `status: str`. The merged
descriptor's `equipment_status` validator already pins the
value-domain against the live `EquipmentStatus` enum (the #570
review lesson).

## 4. R1 Target Output (for the later, separately opted-in impl PR)

New pure module
`src/yuantus/meta_engine/services/maintenance_db_resolver_contract.py`:

- `EquipmentRow` — frozen Pydantic v2, `extra="forbid"`. Subset of
  `meta_maintenance_equipment` columns the mapping needs:
  - `id: str` (non-empty)
  - `status: str` (non-Optional — column is nullable=False; see §3
    Policy D)
  - `workcenter_id: Optional[str] = None` (mirrors the real nullable
    column; the merged descriptor's non-empty validator raises if
    the resolver propagates a falsy value)

  Field names mirror the column names (drift-guarded).
- `MaintenanceRequestRow` — frozen Pydantic v2, `extra="forbid"`.
  Subset of `meta_maintenance_requests` columns the mapping needs:
  - `id: str` (non-empty)
  - `equipment_id: str` (non-empty)
  - `state: str` (validated ∈ `MaintenanceRequestState` values)

  Field names mirror the column names (drift-guarded). `state` is
  NOT typed as the enum — keeping it `str` mirrors the SQLAlchemy
  storage type and the merged descriptor's storage convention.
- Module-level `_ACTIVE_REQUEST_STATES` — the frozenset whose
  contents are decided by the §3 Policy A reviewer ratification:
  - Option A1 ratified → `{DRAFT.value, SUBMITTED.value, IN_PROGRESS.value}`;
  - Option A2 ratified (author recommendation) →
    `{SUBMITTED.value, IN_PROGRESS.value}` (matches the bridge's
    `_BLOCKING_REQUEST_STATES` exactly — and the impl-PR test must
    `assert _ACTIVE_REQUEST_STATES == _BLOCKING_REQUEST_STATES`).
  A drift-guard test pins the chosen set against the live
  `MaintenanceRequestState` enum so an enum addition triggers an
  explicit policy review rather than silently mis-classifying.
- `resolve_workcenter_maintenance_descriptor(equipment_row, request_rows=()) -> WorkcenterMaintenanceDescriptor`
  — pure; applies §3 Policy A (first non-terminal in input order)
  and Policy B (raise on id mismatch); returns the **merged**
  `WorkcenterMaintenanceDescriptor` (imported, not reimplemented).
- `resolve_workcenter_maintenance_descriptors(pairs) -> tuple[...]`
  — batch over `Sequence[Tuple[EquipmentRow, Sequence[MaintenanceRequestRow]]]`;
  deterministic (input order preserved across equipment).

No DB read, no `session`, no `eval`, no plugin edit, no enforcement.
Imports **only** the merged
`maintenance_workorder_bridge_contract.WorkcenterMaintenanceDescriptor`
plus the maintenance enums (value-domain — the same two the merged
bridge already imports).

## 5. Tests Required (in the later impl PR)

New `test_maintenance_db_resolver_contract.py`:

- Row DTOs: frozen, `extra=forbid`, non-empty
  `id`/`equipment_id`/`workcenter_id` (via the merged descriptor's
  validator when propagated), enum-domain `state`.
- **`test_resolver_picks_first_active_request_state_in_input_order`
  (MANDATORY, exactly named)** — single equipment with mixed
  requests; the **first active state in input order** is returned
  for `active_request_state`; non-active and terminal-only inputs
  yield `None`; empty `request_rows` yields `None`. Parametrized
  to cover each member of the §3 Policy A ratified
  `_ACTIVE_REQUEST_STATES` winning when it is the first active in
  input order; and the complementary states being skipped. The
  *exact* set asserted is whichever the reviewer ratifies (A1 vs.
  A2 vs. A3) — the impl PR materialises this once the taskbook
  merges.
- **`test_resolver_active_set_aligns_with_ratified_policy_a`
  (MANDATORY, exactly named)** — pins the §3 Policy A ratification
  in code: `_ACTIVE_REQUEST_STATES` equals the ratified set, and
  (for Option A2 if chosen) `_ACTIVE_REQUEST_STATES ==
  _BLOCKING_REQUEST_STATES` from the merged bridge contract. An
  enum addition or a policy drift fails this test loudly.
- **`test_resolver_rejects_mismatched_equipment_request_pair`
  (MANDATORY, exactly named)** — any
  `request_row.equipment_id != equipment_row.id` → `ValueError`;
  pins the §3 Policy B strict reading (parametrized: mismatch in
  the only row; mismatch in a row that would otherwise be
  filtered-as-non-active).
- **`test_resolver_output_is_the_merged_workcenter_descriptor`
  (MANDATORY, exactly named)** — the return value is an instance of
  the merged
  `maintenance_workorder_bridge_contract.WorkcenterMaintenanceDescriptor`
  and the resolved descriptors feed `evaluate_workcenter_readiness`
  unchanged (compose proof, no DB).
- Batch: order preserved; one equipment's mismatch propagates as
  `ValueError`.
- **Drift guards**: `EquipmentRow` fields ⊆
  `Equipment.__table__.columns`; `MaintenanceRequestRow` fields ⊆
  `MaintenanceRequest.__table__.columns`; `_ACTIVE_REQUEST_STATES`
  pinned against the ratified §3 Policy A set (see the
  `test_resolver_active_set_aligns_with_ratified_policy_a`
  MANDATORY test above); the produced descriptor's field set
  equals `WorkcenterMaintenanceDescriptor.model_fields` (reuse,
  not reimplement);
  `Equipment.__table__.columns["workcenter_id"].nullable is True`
  (pins the soft-link assumption Policy C is built on).
- **Purity guard** (AST): module imports nothing matching
  `yuantus.database` / `sqlalchemy` / `parallel_tasks_service` /
  `_router` / `plugins` / `_service`; imports **only**
  `maintenance_workorder_bridge_contract` and the maintenance enums
  module; contains no `session`/DB call.
- **No-evaluate/no-assert (AST)**: module does not call
  `evaluate_workcenter_readiness` or `assert_workcenter_ready`; no
  `assert_*` callable is defined.

The R2 portfolio drift guard
(`test_odoo18_r2_portfolio_contract.py`) must stay green.

## 6. Verification Commands (for the impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_maintenance_db_resolver_contract.py \
  src/yuantus/meta_engine/tests/test_maintenance_workorder_bridge_contract.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_odoo18_r2_portfolio_contract.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/maintenance_db_resolver_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

## 7. DEV/verification MD requirements (impl PR)

Add `docs/DEV_AND_VERIFICATION_ODOO18_MAINTENANCE_DB_RESOLVER_CONTRACT_R1_20260517.md`
+ index registration. Must document: (a) the pure row→descriptor
boundary (caller fetches; contract never queries); (b) the
non-terminal-state surfacing rule and **why** `DRAFT` is honestly
surfaced rather than collapsed-to-None (bridge's
blocking-vs-non-terminal distinction); (c) the strict-reading
id-mismatch rule and why it is input validation, not bridge
enforcement; (d) the soft-link nature of `Equipment.workcenter_id`
and the explicit non-goal of FK hardening; (e) the merged
`WorkcenterMaintenanceDescriptor` reused unchanged.

## 8. Non-Goals (hard boundaries for the impl PR)

- **No DB read / no `session`** — caller-supplied rows only; the
  actual query is a separate later opt-in.
- **No service/router/plugin wiring** —
  `MaintenanceService`/`maintenance_router`/manufacturing-side
  callers are not edited.
- **No bridge-contract enforcement** —
  `evaluate_workcenter_readiness` /`assert_workcenter_ready` are
  reused **unchanged**; the resolver only produces descriptors, it
  does not decide ready/blocked.
- **No edit to `maintenance_workorder_bridge_contract`,
  `maintenance/models.py`, or `maintenance/service.py`**.
- **No FK hardening for `Equipment.workcenter_id`** — explicitly
  the bridge contract's separate follow-up (c); changing the
  column's nullability is a schema change, out of scope.
- No schema / migration / tenant-baseline / feature flag / runtime
  wiring.
- No contact with the other R2 contracts beyond importing the
  merged `WorkcenterMaintenanceDescriptor` and the maintenance
  enums.
- `.claude/` and `local-dev-env/` stay out of git.

## 9. Decision Gate / Handoff

Doc-only. Implementation owned by Claude Code **only after this
taskbook is merged AND a separate explicit opt-in is given**, on
branch
`feat/odoo18-maintenance-db-resolver-contract-r1-20260517`.

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- An actual DB resolver that **queries**
  `meta_maintenance_equipment` + `meta_maintenance_requests` and
  feeds these row DTOs (touches the DB — separate).
- Wiring the resolved descriptors into a manufacturing-side caller
  of `assert_workcenter_ready` (plugin + runtime — separate; the
  merged `assert_workcenter_ready` is the enforcement seam, also
  separate).
- `Equipment.workcenter_id` FK hardening (schema — separate; the
  bridge contract's documented follow-up (c)).

## 10. Reviewer Focus

- §3 Policy A is **open for reviewer ratification** — please
  choose one of:
  - **A1** — surface non-terminal incl. `DRAFT`
    (matches `get_maintenance_queue_summary`);
  - **A2** (author recommendation) — surface only
    `{SUBMITTED, IN_PROGRESS}` (matches both
    `get_preventive_schedule` and the bridge's
    `_BLOCKING_REQUEST_STATES`);
  - **A3** — no filter (NOT recommended).

  The impl PR materialises `_ACTIVE_REQUEST_STATES` and the
  MANDATORY `test_resolver_picks_first_active_request_state_in_input_order`
  parametrisation from the ratified choice.
- Is the id-mismatch rule (§3 Policy B) read strictly —
  unconditional on whether the mismatching row would have been
  selected?
- Is `EquipmentRow.status` typed as `str` (non-Optional) so the
  `nullable=False` column is mirrored, and
  `EquipmentRow.workcenter_id` typed `Optional[str] = None` to
  mirror the soft link?
- Is the contract pure (no DB/session/service import; allows only
  the merged bridge contract + maintenance enums) and does it
  reuse the merged `WorkcenterMaintenanceDescriptor` unchanged
  (drift-guarded)?
- Are the row DTO field sets proper subsets of the real table
  columns, and is `_NON_TERMINAL_REQUEST_STATES` pinned exactly
  against the live `MaintenanceRequestState` enum?
- Did anything add a DB read, edit the bridge contract /
  maintenance service / maintenance router, harden the
  `Equipment.workcenter_id` FK, or add enforcement? It must not.
