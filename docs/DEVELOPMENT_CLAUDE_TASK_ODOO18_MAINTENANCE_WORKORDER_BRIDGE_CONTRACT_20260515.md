# Claude Taskbook: Odoo18 Maintenance ↔ Workorder Bridge Contract R1

Date: 2026-05-15

Type: **Doc-only taskbook.** Changes no runtime, no schema, no plugin.
Specifies the contract a later, separately opted-in implementation PR
will deliver. Merging this taskbook does NOT authorize that code.

## 1. Purpose

R2 candidate (maintenance↔workorder bridge,
`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md` §3.2 `mrp_maintenance`
row, §四.9). Odoo `mrp_maintenance` surfaces equipment maintenance state
to the manufacturing side (a workcenter blocked by an open maintenance
request is not ready to run). Yuantus has both domains but **no
validated bridge** between them.

R1 follows the now-proven pattern (consumption MES `6973a4c`,
pack-and-go bridge `c7e6fd5`): a small **pure** contract module + tests +
DEV/verification MD. Default no-op: no route, no DB read, no schema, no
flag. The DB resolver and any manufacturing-side wiring are separate,
later opt-ins.

## 2. Current Baseline (grounded)

Evidence (read before implementing):

- `src/yuantus/meta_engine/maintenance/models.py`:
  - `Equipment` (`meta_maintenance_equipment`) has
    `workcenter_id = Column(String, nullable=True)` — a **bare,
    unvalidated, no-FK** soft link to a workcenter. This is the only
    existing maintenance↔manufacturing coupling today.
  - `EquipmentStatus` enum: `operational`, `in_maintenance`,
    `out_of_service`, `decommissioned`.
  - `MaintenanceRequest` (`meta_maintenance_requests`) has
    `equipment_id` but **no** `workcenter_id` / `routing_id` /
    `operation_id` / workorder link of any kind.
  - `MaintenanceRequestState` enum: `draft`, `submitted`,
    `in_progress`, `done`, `cancelled`.
- `src/yuantus/meta_engine/maintenance/service.py`
  `get_equipment_readiness_summary(workcenter_id=...)` already rolls up
  equipment **status** counts per workcenter — but it is **DB-bound**
  and keyed on `EquipmentStatus` only; it does not consider open
  `MaintenanceRequest`s and is not a pure, testable contract.
- `src/yuantus/meta_engine/manufacturing/models.py`: `WorkCenter`
  (`meta_workcenters`) and `Operation` carry `workcenter_id` /
  `workcenter_code`. There is no consumer that asks "is this workcenter
  blocked by maintenance?".

**Gap the contract closes:** there is no pure, testable function that,
given resolved facts, answers *"is workcenter W ready, or is it blocked
by equipment that is out of service / under an active maintenance
request?"* — and the one existing rollup ignores open requests entirely.

**Design tension (resolve in doc, not code):** readiness needs each
equipment's `(workcenter_id, equipment_status, active_request_state)`. A
*pure* contract cannot read the DB, so it operates over
**caller-supplied descriptors**. A DB resolver building those from real
`Equipment` / `MaintenanceRequest` rows is a separate, later opt-in —
the same split used by the consumption and pack-and-go contracts.

## 3. R1 Target Output (for the later, separately opted-in impl PR)

New pure module, e.g.
`src/yuantus/meta_engine/services/maintenance_workorder_bridge_contract.py`:

- `WorkcenterMaintenanceDescriptor` — frozen Pydantic v2,
  `extra="forbid"`:
  - `workcenter_id: str` — stripped, non-empty
  - `equipment_id: str` — stripped, non-empty
  - `equipment_status: str` — **must validate** against the live
    `EquipmentStatus` values (positive confirmation — an unknown status
    is rejected, not silently treated as available; this is the #570
    review lesson baked in)
  - `active_request_state: str | None` — if present, **must validate**
    against the live `MaintenanceRequestState` values; `None` means
    "no active maintenance request for this equipment"
  Field names / enum domains deliberately mirror the maintenance model
  so a future DB resolver maps 1:1 and a drift test asserts alignment.
- `WorkcenterReadinessReport` — frozen dataclass, one per distinct
  `workcenter_id`:
  - `workcenter_id: str`
  - `total_equipment: int`
  - `blocked: list[str]` — equipment ids that fail readiness
  - `degraded: list[str]` — equipment ids that are impaired but do not
    fail readiness (informational, like `stale` in the pack-and-go
    contract)
  - `ready: bool` — `True` iff `blocked` is empty
- `evaluate_workcenter_readiness(descriptors)
  -> list[WorkcenterReadinessReport]` — **pure** (no DB, no I/O),
  never raises, no enforcement flag. Groups descriptors by
  `workcenter_id`; deterministic ordering (sorted by `workcenter_id`).
- `assert_workcenter_ready(descriptors, *, workcenter_id) -> None` —
  thin raiser: `ValueError` listing blocked equipment ids when that
  workcenter is not ready; `None` when ready; raises `KeyError`-style
  `ValueError` if the workcenter is absent from the descriptors (an
  absent workcenter is **not** vacuously ready — distinct from the
  pack-and-go empty-bundle decision, because here "no descriptors for W"
  means "unknown", and unknown must not pass; document this explicitly).

### Readiness rule (pinned)

For one equipment descriptor:

- **blocked** iff
  `equipment_status in {out_of_service, decommissioned}` **OR**
  `active_request_state in {submitted, in_progress}`.
- **degraded** (informational, does NOT fail `ready`) iff not blocked
  **and** `equipment_status == in_maintenance`.
- otherwise nominal (`operational`, no active blocking request).

`draft` and `cancelled`/`done` request states are **not** blocking
(draft = not yet active; cancelled/done = closed). A workcenter is
`ready` iff it has zero `blocked` equipment. `degraded` never affects
`ready` — same "informational tier never fails the gate" stance as the
pack-and-go contract's `stale`.

## 4. Tests Required (in the later impl PR)

New `test_maintenance_workorder_bridge_contract.py`:

- Descriptor validation: empty `workcenter_id` / `equipment_id`
  rejected; unknown `equipment_status` rejected; unknown
  `active_request_state` rejected; `active_request_state=None` accepted.
- All-operational, no requests → `ready=True`, empty blocked/degraded.
- `out_of_service` / `decommissioned` equipment → blocked, `ready=False`.
- `active_request_state` `submitted` / `in_progress` → blocked,
  `ready=False`, even if `equipment_status=operational`.
- `active_request_state` `draft` / `done` / `cancelled` → not blocked.
- **`draft` distinction (pin this explicitly)**: a `draft` request →
  `ready=True` for the workcenter. This intentionally differs from
  `MaintenanceService.get_maintenance_queue_summary`, which counts
  `draft` into the active maintenance queue. The two answer different
  questions ("is there queued maintenance work?" vs. "is this workcenter
  blocked *right now*?"); a `draft` request is not yet active so it does
  not block readiness. The impl PR MUST include a test asserting a
  `draft`-only descriptor yields `ready=True`, with a comment citing
  this deliberate divergence so a future reader does not "fix" it into
  agreement with the queue summary.
- `equipment_status=in_maintenance` with no blocking request → degraded,
  still `ready=True`.
- Multiple workcenters → one report each, sorted by `workcenter_id`;
  per-workcenter `total_equipment` correct.
- `assert_workcenter_ready`: returns `None` when ready; raises listing
  blocked ids when not; raises for an absent workcenter (not vacuously
  ready).
- Purity guard: AST import scan asserts the module imports nothing from
  `yuantus.database` / `sqlalchemy` / `maintenance.service` / a router /
  `plugins`; evaluator has no DB parameter.
- **Drift guard**: the descriptor's accepted `equipment_status` value
  set equals `{s.value for s in EquipmentStatus}` and its
  `active_request_state` set equals
  `{s.value for s in MaintenanceRequestState}` (introspected from
  `maintenance.models`). If those enums change, the contract fails
  loudly rather than silently diverging.

Doc-index trio stays green for the impl PR's DEV/verification MD.

## 5. Verification Commands (for the impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_maintenance_workorder_bridge_contract.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/maintenance_workorder_bridge_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

## 6. Non-Goals (hard boundaries for the impl PR)

- **No route.** No endpoint; no change to the maintenance or
  manufacturing routers.
- **No table / migration / tenant baseline / schema change.** In
  particular, do **not** add a `workcenter_id` FK or any column to
  `MaintenanceRequest` / `Equipment`.
- **No DB reads in the contract.** Caller-supplied descriptors only. A
  DB resolver is a separate opt-in.
- **No change to `MaintenanceService` / `get_equipment_readiness_summary`
  / manufacturing services.**
- **No feature flag / production setting.**
- **No contact with workorder version-lock R1, the consumption MES
  contract, or the pack-and-go bridge contract.** This is a new
  independent pure module.
- `.claude/` and `local-dev-env/` stay out of git.

## 7. Decision Gate / Handoff

Doc-only. The implementation PR (pure module + tests +
DEV/verification MD) is owned by Claude Code **only after this taskbook
is merged AND a separate explicit opt-in is given**, on branch:

`feat/odoo18-maintenance-workorder-bridge-contract-r1-20260515`

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- A DB resolver building `WorkcenterMaintenanceDescriptor`s from real
  `Equipment` + `MaintenanceRequest` rows (joining on the loose
  `Equipment.workcenter_id`).
- Surfacing readiness to the manufacturing/workorder side (a consumer
  that calls `assert_workcenter_ready` before allowing an operation to
  start).
- Any schema hardening of the `Equipment.workcenter_id` link (FK /
  validation) — explicitly its own decision.

## 8. Reviewer Focus

- Is the contract genuinely pure (no DB/Session/service/router import)?
- Does the drift guard introspect the **real** `EquipmentStatus` /
  `MaintenanceRequestState` enums (not a hard-coded copy)?
- Is the blocked/degraded rule pinned unambiguously, and does
  `degraded` correctly never fail `ready` (consistent with the
  pack-and-go `stale` precedent)?
- Is "absent workcenter is NOT vacuously ready" honoured (contrast with
  the pack-and-go empty-bundle decision — different on purpose, and the
  difference must be documented)?
- Did anything add a route / schema / DB read, or touch the prior
  contracts? It must not.
