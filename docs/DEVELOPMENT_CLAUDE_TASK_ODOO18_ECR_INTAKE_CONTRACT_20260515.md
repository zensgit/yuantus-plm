# Claude Taskbook: Odoo18 ECR Intake Contract R1

Date: 2026-05-15

Type: **Doc-only taskbook.** Changes no runtime, no schema, no plugin.
Specifies the contract a later, separately opted-in implementation PR
will deliver. Merging this taskbook does NOT authorize that code.

## 1. Purpose

R2 candidate **ECR intake** (`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md`
§四.2). Odoo's change workflow has an Engineering **Change Request**
(ECR) intake step that precedes the Engineering **Change Order** (ECO).
Yuantus has ECO but **no ECR intake**: an ECO is created already
mid-pipeline. There is no typed, validated boundary for "someone is
requesting a change" before it becomes an ECO.

R1 follows the now-proven contract-first pattern (consumption MES
`6973a4c`, pack-and-go bridge `c7e6fd5`, maintenance bridge `ca6755f`):
a small **pure** module + tests + DEV/verification MD. Default no-op: no
route, no DB read, no schema, no flag, and **it does not create ECOs**.
Wiring the intake to actually call `ECOService.create_eco` is a
separate, later opt-in.

## 2. Current Baseline (grounded)

Evidence (read before implementing):

- **No ECR entity exists.** `src/yuantus/meta_engine/services/change_service.py`
  is a **DEPRECATED** ECM shim (its own header: "superseded by
  ECOService … No new code should import ChangeService"). The only
  occurrence of "ECR" in the codebase is a comment there ("Pending
  ECR/ECOs affecting this item") — no model, no DTO, no intake.
- `src/yuantus/meta_engine/models/eco.py`:
  - `ECO` (`meta_ecos`) is created directly with no requester / reason /
    origin / intake fields; its `state` starts at `draft`
    (`ECOState`: draft/progress/suspended/conflict/approved/done/
    canceled).
  - `ECOType` enum: `bom`, `product`, `document`.
  - `ECOPriority` enum: `low`, `normal`, `high`, `urgent`.
- `src/yuantus/meta_engine/services/eco_service.py` `ECOService.create_eco`
  is the canonical ECO-creation entrypoint. Signature:
  `create_eco(name: str, eco_type: str, product_id: Optional[str],
  description: Optional[str] = None, priority: str = "normal",
  user_id: Optional[int] = 1, effectivity_date: Optional[datetime] =
  None) -> ECO`. It raises if `eco_type == "bom"` and `product_id` is
  missing, and runs a permission check.

**Gap the contract closes:** there is no pure, typed, validated
representation of an inbound change *request*, nor a checked mapping from
such a request to the exact `create_eco` arguments. Today a caller would
hand-roll `create_eco(...)` kwargs with no normalization, no enum
validation, and no stable reference for dedupe/triage.

**Design tension (resolve in doc, not code):** turning an ECR into an
ECO requires a DB write (`create_eco`) and a permission check. A *pure*
contract must not do that. So R1 delivers only the **validated intake +
the pure mapping to `create_eco` kwargs**. Actually invoking
`create_eco` (the "wiring") and any ECR persistence are separate, later
opt-ins — the same split used by the consumption MES contract (which
deferred ingestion wiring) and the bridge contracts (which deferred DB
resolvers).

## 3. R1 Target Output (for the later, separately opted-in impl PR)

New pure module, e.g.
`src/yuantus/meta_engine/services/ecr_intake_contract.py`:

- `ChangeRequestIntake` — frozen Pydantic v2, `extra="forbid"`:
  - `title: str` — stripped, non-empty (becomes ECO `name`)
  - `change_type: str` — must validate against the **live** `ECOType`
    values (`bom`/`product`/`document`); unknown ⇒ `ValueError`
    (fail-fast, the #570 lesson)
  - `product_id: str | None` — required (non-empty) **iff**
    `change_type == "bom"` (mirror `create_eco`'s own invariant so the
    intake fails at the boundary, not deep in `create_eco`)
  - `priority: str` (default `"normal"`) — must validate against the
    **live** `ECOPriority` values
  - `reason: str | None` — free-text justification; flows into the ECO
    `description` envelope
  - `requester_user_id: int | None` — becomes `create_eco`'s `user_id`.
    `EcoDraftInputs.user_id` keeps the value **as-is including `None`**
    (the 1:1 kwarg mirror below is preserved — `user_id` is always
    passed). No "leave unset": `create_eco` already normalizes a falsy
    `user_id` to `1` internally (`user_id_int = int(user_id) if user_id
    else 1`), so passing `user_id=None` is correct and equivalent to the
    default without breaking the 1:1 mapping.
  - `effectivity_date: datetime | None` — passthrough; tz-aware →
    naive-UTC normalisation (reuse the consumption-contract precedent)
- `EcoDraftInputs` — frozen dataclass mirroring the `create_eco`
  keyword set **1:1** (`name, eco_type, product_id, description,
  priority, user_id, effectivity_date`) so a drift test can assert
  alignment with the real signature.
- `derive_change_request_reference(intake) -> str` — deterministic
  `sha256` over stable fields (`title`, `change_type`, `product_id`,
  `requester_user_id`). **Recorded only, NOT enforced** — no dedupe, no
  DB. Same deferral as the consumption idempotency key.
- `map_change_request_to_eco_draft_inputs(intake) -> EcoDraftInputs` —
  **pure** (no DB, no `create_eco` call). `description` is composed as
  the requester `reason` plus a reserved intake envelope carrying the
  reference + contract version (mirror the consumption `_ingestion`
  envelope; reject a caller-supplied collision if `reason` is
  structured — keep `reason` plain text in R1, so just compose).

R1 explicitly does **not** call `create_eco`, persist an ECR, add a
route, or change `ECOService`.

## 4. Tests Required (in the later impl PR)

New `test_ecr_intake_contract.py`:

- Intake validation: empty `title` rejected; unknown `change_type`
  rejected (fail-fast); unknown `priority` rejected; `priority` defaults
  to `normal`; tz-aware `effectivity_date` normalised to naive-UTC.
- **`bom` requires product_id**: `change_type="bom"` with no
  `product_id` is rejected at the intake boundary; `product`/`document`
  without `product_id` is accepted (mirrors `create_eco`'s invariant —
  pin this with a comment so it stays aligned).
- `derive_change_request_reference` deterministic for identical input;
  differs when any stable field differs; sha256-hex shape.
- Mapper output kwargs **exactly** equal the `create_eco` parameter set
  (introspected, excluding `self`); `description` carries the reason +
  reference envelope; mapper does not mutate the intake.
- Round-trippability (no DB): the mapper output dict is acceptable to
  `inspect.signature(ECOService.create_eco).bind(**kwargs)` without
  `TypeError` — proves shape compatibility without invoking it.
- Purity guard: AST import scan asserts the module imports nothing from
  `yuantus.database` / `sqlalchemy` / `eco_service` / a router /
  `plugins`; it MAY import the `eco` model enums (the value-domain
  source). `evaluate`/mapper has no DB parameter.
- **Drift guard**: accepted `change_type` set == `{t.value for t in
  ECOType}`; accepted `priority` set == `{p.value for p in
  ECOPriority}`; `EcoDraftInputs` fields == the `create_eco` parameter
  set (introspected) — a rename in `create_eco` or the enums fails this
  loudly.

Doc-index trio stays green for the impl PR's DEV/verification MD.

## 5. Verification Commands (for the impl PR)

```bash
.venv/bin/python -m pytest -q \
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
  src/yuantus/meta_engine/services/ecr_intake_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

## 6. Non-Goals (hard boundaries for the impl PR)

- **No route.** No ECR endpoint; no change to the ECO routers.
- **No table / migration / tenant baseline / schema.** No ECR entity is
  persisted in R1.
- **No DB read or write in the contract.** In particular it does **not**
  call `ECOService.create_eco`.
- **No change to `ECOService` / `create_eco` / the deprecated
  `ChangeService`.**
- **No dedupe enforcement.** The reference is derived/recorded only.
- **No feature flag / production setting.**
- **No contact with the workorder version-lock, consumption MES,
  pack-and-go, or maintenance bridge contracts.** New independent pure
  module.
- `.claude/` and `local-dev-env/` stay out of git.

## 7. Decision Gate / Handoff

Doc-only. The implementation PR (pure module + tests +
DEV/verification MD) is owned by Claude Code **only after this taskbook
is merged AND a separate explicit opt-in is given**, on branch:

`feat/odoo18-ecr-intake-contract-r1-20260515`

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- **ECR→ECO wiring**: a caller that takes a validated
  `ChangeRequestIntake`, maps it, and actually invokes
  `ECOService.create_eco(**EcoDraftInputs.as_kwargs())` (touches
  DB/permissions — its own taskbook + PR).
- **ECR persistence**: an `EngineeringChangeRequest` table + lifecycle
  (intake → triage → spawned ECO link). Schema change — its own
  decision.
- **ECR→ECO dedupe enforcement** using the derived reference.

## 8. Reviewer Focus

- Is the contract genuinely pure (no DB / `eco_service` / router import;
  must not call `create_eco`)?
- Does the drift guard introspect the **real** `create_eco` signature
  and the **real** `ECOType`/`ECOPriority` enums (not hard-coded
  copies)?
- Is the `bom ⇒ product_id` invariant enforced at the intake boundary
  and pinned with a comment citing the `create_eco` alignment?
- Is "no `create_eco` call / no persistence in R1" unambiguous, with
  wiring + persistence clearly deferred to separate opt-ins?
- Did anything add a route / schema / DB or touch the prior four
  contracts? It must not.
