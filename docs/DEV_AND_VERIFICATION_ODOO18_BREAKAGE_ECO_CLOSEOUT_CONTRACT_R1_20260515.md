# Odoo18 Breakage → ECO Closeout Contract R1 — Development and Verification

Date: 2026-05-15

## 1. Goal

Implement R1 of the breakage→ECO closeout taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_BREAKAGE_ECO_CLOSEOUT_CONTRACT_20260515.md`,
merged `a36cddd`). A **pure, typed bridge** from a `BreakageIncident`
descriptor to the shipped ECR intake contract's `ChangeRequestIntake`,
so a field breakage that is a design defect can loop back into
engineering.

R1 is **pure, parallel, behavior-preserving**: a module + tests + this
MD. No DB, no `create_eco`, no `BreakageIncident` write, no
state-machine edit, no service/router/schema change. It **reuses**
`ecr_intake_contract` as a pure dependency.

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/breakage_eco_closeout_contract.py`
- `src/yuantus/meta_engine/tests/test_breakage_eco_closeout_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_BREAKAGE_ECO_CLOSEOUT_CONTRACT_R1_20260515.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

`BreakageIncidentService`, the breakage router, `ecr_intake_contract`
(reused unchanged), ORM models, and the prior six Odoo18 contracts are
**unchanged**.

## 3. Contract

### 3.1 `BreakageEcoClosureDescriptor` (Pydantic v2, frozen, `extra="forbid"`)

Fields mirror `BreakageIncident` columns: `description` (non-empty),
`status`, `severity` (default `"medium"`), `incident_code`,
`product_item_id`, `bom_id`, `version_id`. `status`/`severity` are
trimmed + lowercased; optional ids blank→`None`.

### 3.2 RATIFIED policy constants (binding, exactly named)

- `eligible_statuses = frozenset({"resolved", "closed"})` — §3.1 of the
  taskbook. `is_breakage_eligible_for_design_loopback` returns `True`
  iff the normalized status ∈ this set; `open`, `in_progress`, and
  **any unknown status** are NOT eligible.
- `severity_to_priority = {"critical":"urgent", "high":"high",
  "medium":"normal", "low":"low"}` — §3.2. `severity_priority(severity)`
  returns the table value, and **any severity not in the table →
  `"normal"`**. This `unknown → normal` rule is a deliberate,
  documented **conservative *downgrade* policy** — NOT a silent
  fallback: dirty data is neither escalated to `urgent`/`high` nor
  dropped.

### 3.3 Functions

- `is_breakage_eligible_for_design_loopback(descriptor) -> bool` — pure.
- `severity_priority(severity) -> str` — pure, total (ratified table +
  unknown→normal).
- `derive_breakage_change_reference(descriptor) -> str` — deterministic
  sha256 over `(incident_code, product_item_id, version_id)`; recorded
  in the reason envelope only, **not enforced** (no dedupe/DB).
- `map_breakage_to_change_request_intake(descriptor) -> ChangeRequestIntake`
  — pure; raises `ValueError` if not eligible. `change_type="bom"`
  **only** when both `bom_id` and `product_item_id` are present (so the
  ECR contract's own bom⇒product_id invariant always holds);
  otherwise `"product"`. `title` deterministic from `incident_code`;
  `reason` = description + a reserved `[breakage-eco-closeout …]`
  envelope (human-readable, **NOT** a parsing wire format — same stance
  as the ECR contract); `priority` per the ratified severity table;
  `requester_user_id=None`.

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_breakage_eco_closeout_contract.py`
(test groups; counts are a point-in-time snapshot and grow as cases are
added):

- Descriptor: frozen, `extra=forbid`, empty `description` rejected,
  status/severity normalized, blanks→None.
- **`test_resolved_and_closed_are_eligible_only` (MANDATORY, named
  exactly)** — pins ratified §3.1: `resolved`/`closed` eligible
  (case-insensitive); `open`, `in_progress`, `canceled`, and unknown
  NOT eligible; asserts `eligible_statuses == {"resolved","closed"}`.
- **`test_unknown_severity_maps_to_normal_by_ratified_policy`
  (MANDATORY, named exactly)** — pins ratified §3.2: the exact table,
  case-insensitivity, and that every unrecognized/blank severity →
  `"normal"` (conservative downgrade, not silent).
- Mapping: bom+product → `change_type="bom"`; bom without
  product_item_id → falls back to `"product"` (pinned edge so the
  produced `ChangeRequestIntake` always satisfies its own bom⇒product_id
  invariant); no bom → `"product"`; title/reason envelope + embedded
  reference; **composes through** `map_change_request_to_eco_draft_inputs`
  with no DB; not-eligible → `ValueError`.
- Reference: deterministic, identity-field-keyed, sha256-hex.
- Purity guard: AST import scan — module imports nothing from
  `yuantus.database` / `sqlalchemy` / `parallel_tasks_service` / a
  router / `plugins`; it MAY (and does) import
  `yuantus.meta_engine.services.ecr_intake_contract`.
- Drift guards: descriptor field set ⊆ `BreakageIncident.__table__`
  columns; `eligible_statuses` ⊆ the breakage status vocabulary
  (`BreakageIncidentService._HELPDESK_PROVIDER_TO_INCIDENT_STATUS`
  values, introspected); `severity_to_priority` codomain ∪ `{normal}`
  ⊆ `ECOPriority` values — a change on either side fails loudly.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_breakage_eco_closeout_contract.py \
  src/yuantus/meta_engine/tests/test_ecr_intake_contract.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/breakage_eco_closeout_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

Observed as of 2026-05-15: contract tests all passed; ECR-intake
regression all passed (compose dependency); doc-index trio passed;
py_compile clean; `git diff --check` clean.

## 6. Non-Goals (reaffirmed from taskbook §7)

No DB / `create_eco` / `BreakageIncident` write / state-machine edit;
no change to `BreakageIncidentService` or the breakage router; no
route / table / migration / schema / feature flag; no dedupe
enforcement (reference recorded only). `ecr_intake_contract` is reused
unchanged. No contact with the workorder version-lock, consumption
MES, pack-and-go, maintenance, or automation-rule contracts. `.claude/`
and `local-dev-env/` stay out of git.

## 7. Follow-ups (each its own separate opt-in)

- **Breakage→ECR/ECO wiring**: a caller that, when a breakage reaches
  an eligible status, maps it and invokes the ECR intake →
  `create_eco` path (touches DB/permissions/state machine).
- **Breakage state-machine integration** (an explicit "spawn change"
  action / status).
- **Dedupe enforcement** using the derived reference.
