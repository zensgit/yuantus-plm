# Odoo18 Maintenance ↔ Workorder Bridge Contract R1 — Development and Verification

Date: 2026-05-15

## 1. Goal

Implement R1 of the maintenance↔workorder bridge contract taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_MAINTENANCE_WORKORDER_BRIDGE_CONTRACT_20260515.md`,
merged `02409c5`). A pure contract answering "is a workcenter blocked by
maintenance?" over caller-supplied descriptors, reusing the live
maintenance enums.

R1 is **pure and default no-op**: a module + tests + this MD. No route,
no schema, no DB read, no service change, no flag. The DB resolver and
the manufacturing-side wiring are separate, later opt-ins.

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/maintenance_workorder_bridge_contract.py`
- `src/yuantus/meta_engine/tests/test_maintenance_workorder_bridge_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_MAINTENANCE_WORKORDER_BRIDGE_CONTRACT_R1_20260515.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

`MaintenanceService`, the maintenance/manufacturing routers, the ORM
models, and the prior three Odoo18 contracts are **unchanged**.

## 3. Contract

### 3.1 `WorkcenterMaintenanceDescriptor` (Pydantic v2, frozen, `extra="forbid"`)

| Field | Type | Notes |
|---|---|---|
| `workcenter_id` | `str` | stripped, non-empty |
| `equipment_id` | `str` | stripped, non-empty |
| `equipment_status` | `str` | must be a value of the live `EquipmentStatus`; unknown ⇒ `ValueError` (fail-fast, the #570 lesson) |
| `active_request_state` | `str \| None` | if present, must be a value of the live `MaintenanceRequestState`; `None` = no active request |

Value domains are derived at import time from the real enums in
`yuantus.meta_engine.maintenance.models` — not hard-coded — so the drift
guard is meaningful.

### 3.2 `WorkcenterReadinessReport` (frozen dataclass)

`workcenter_id, total_equipment, blocked, degraded, ready`.

- `ready = (blocked is empty)`.
- `degraded` is informational and **never** affects `ready` (same tier
  as the pack-and-go contract's `stale`).

### 3.3 Readiness rule (pinned)

Per equipment descriptor:

- **blocked** iff `equipment_status ∈ {out_of_service, decommissioned}`
  **or** `active_request_state ∈ {submitted, in_progress}`.
- **degraded** iff not blocked **and**
  `equipment_status == in_maintenance`.
- otherwise nominal.

`draft` / `done` / `cancelled` request states are non-blocking.

**Deliberate `draft` divergence (pinned by test):**
`MaintenanceService.get_maintenance_queue_summary` counts `draft` into
the *active maintenance queue*. This contract intentionally treats
`draft` as **non-blocking** for workcenter readiness — the two answer
different questions ("is there queued maintenance work?" vs. "is this
workcenter blocked right now?"). A draft request is not yet active.
`test_draft_request_does_not_block_readiness` carries a comment citing
this divergence so a future reader does not "fix" it into agreement with
the queue summary.

### 3.4 Functions

- `evaluate_workcenter_readiness(descriptors) -> list[WorkcenterReadinessReport]`
  — pure, no DB/I-O, **never raises**, **no enforcement flag**. One
  report per distinct `workcenter_id`, sorted by `workcenter_id` for
  deterministic output.
- `assert_workcenter_ready(descriptors, *, workcenter_id) -> None` —
  returns `None` when ready, raises `ValueError` otherwise. An
  **absent** workcenter (no descriptor names it) raises — it is **NOT**
  vacuously ready. This is deliberately different from the pack-and-go
  empty-bundle decision: there an empty bundle has no documents to
  violate; here an absent workcenter has *unknown* maintenance state,
  and unknown must not pass.

  The three failure modes carry **machine-matchable prefixes** so a
  caller can react without catching `ValueError` blindly:

  | Prefix | Meaning | Caller guidance |
  |---|---|---|
  | `workcenter_invalid:` | blank `workcenter_id` argument | caller bug — fix the call |
  | `workcenter_blocked:` | known state, currently blocked | transient — a later retry may succeed |
  | `workcenter_unknown:` | no descriptors for this workcenter | not transient — likely resolver/caller bug, do not retry |

  `test_assert_failure_prefixes_are_distinct_discriminators` pins that
  the three prefixes are distinct.

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_maintenance_workorder_bridge_contract.py`
(test groups; counts are a point-in-time snapshot and grow as cases are
added):

- **Descriptor validation**: empty ids rejected; ids stripped; unknown
  `equipment_status` / `active_request_state` rejected fail-fast;
  `None` request state accepted; frozen + `extra=forbid`.
- **Blocked/degraded rule**: all-operational ready; out_of_service /
  decommissioned blocks; submitted / in_progress blocks even if
  operational; done / cancelled do not block; **draft does not block**
  (divergence pin with comment); in_maintenance → degraded but still
  ready; in_maintenance + blocking request → blocked, not degraded.
- **Multi-workcenter**: one report per workcenter, sorted by id,
  per-workcenter `total_equipment` correct; empty input → no reports.
- **Report/raise split**: `evaluate` signature is exactly
  `(descriptors)` and never raises; `assert` returns `None` when ready,
  raises listing blocked ids otherwise, **raises for an absent
  workcenter**, **rejects a blank `workcenter_id` argument**, does not
  raise on degraded-only, and the three failure prefixes
  (`workcenter_invalid` / `workcenter_blocked` / `workcenter_unknown`)
  are asserted distinct.
- **Purity guard**: AST import scan asserts the module imports nothing
  from `yuantus.database` / `sqlalchemy` / `maintenance.service` / a
  router / `plugins`, and *does* import
  `yuantus.meta_engine.maintenance.models` (the enum source);
  `evaluate` has no DB parameter.
- **Enum drift guard**: the accepted `equipment_status` /
  `active_request_state` domains equal `{s.value for s in
  EquipmentStatus}` / `{s.value for s in MaintenanceRequestState}`
  introspected from the real enums; the blocking sets are subsets of
  them; `draft` is asserted **not** in the blocking request set.

## 5. Verification Commands

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

Observed as of 2026-05-15: contract tests all passed; doc-index trio
passed; py_compile clean; `git diff --check` clean.

## 6. Non-Goals (reaffirmed from taskbook §6)

No route; no table / migration / tenant baseline / schema (in particular
no `workcenter_id` FK on `MaintenanceRequest` / `Equipment`); no DB read
in the contract; no change to `MaintenanceService` /
`get_equipment_readiness_summary` / manufacturing services; no feature
flag; no contact with the workorder version-lock R1, consumption MES, or
pack-and-go bridge contracts. `.claude/` and `local-dev-env/` stay out
of git.

## 7. Follow-ups (each its own separate opt-in)

- A DB resolver building `WorkcenterMaintenanceDescriptor`s from real
  `Equipment` + `MaintenanceRequest` rows (joining on the loose
  `Equipment.workcenter_id`).
- Surfacing readiness to the manufacturing/workorder side (a consumer
  calling `assert_workcenter_ready` before an operation starts).
- Any schema hardening of the `Equipment.workcenter_id` link.
