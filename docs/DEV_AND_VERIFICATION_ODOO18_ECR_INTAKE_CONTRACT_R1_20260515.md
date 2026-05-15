# Odoo18 ECR Intake Contract R1 — Development and Verification

Date: 2026-05-15

## 1. Goal

Implement R1 of the ECR intake contract taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_ECR_INTAKE_CONTRACT_20260515.md`,
merged `2b5010f`). A pure, validated intake boundary for an engineering
change *request* that maps to the exact `ECOService.create_eco` keyword
arguments — **without creating an ECO**.

R1 is **pure and default no-op**: a module + tests + this MD. No route,
no schema, no DB read/write, no `create_eco` call, no flag. ECR→ECO
wiring, ECR persistence, and dedupe enforcement are separate, later
opt-ins.

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/ecr_intake_contract.py`
- `src/yuantus/meta_engine/tests/test_ecr_intake_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_ECR_INTAKE_CONTRACT_R1_20260515.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

`ECOService`, the deprecated `ChangeService`, the ECO routers, the ORM
models, and the prior four Odoo18 contracts are **unchanged**.

## 3. Contract

### 3.1 `ChangeRequestIntake` (Pydantic v2, frozen, `extra="forbid"`)

| Field | Type | Notes |
|---|---|---|
| `title` | `str` | stripped, non-empty → becomes ECO `name` |
| `change_type` | `str` | normalized lower, must be a live `ECOType` value (`bom`/`product`/`document`); unknown ⇒ `ValueError` (fail-fast, the #570 lesson) |
| `product_id` | `str \| None` | blank→None; **required (non-empty) iff `change_type == "bom"`** — enforced by a model validator that mirrors `create_eco`'s own invariant |
| `priority` | `str` (default `normal`) | normalized lower, must be a live `ECOPriority` value |
| `reason` | `str \| None` | blank→None; free-text, flows into the ECO `description` envelope |
| `requester_user_id` | `int \| None` | becomes `create_eco`'s `user_id`; `None` kept as-is |
| `effectivity_date` | `datetime \| None` | tz-aware → UTC then naive (column/codebase are naive-UTC) |

Value domains are derived at import time from the real
`ECOType`/`ECOPriority` enums in `yuantus.meta_engine.models.eco` — not
hard-coded — so the drift guard is meaningful.

### 3.2 `EcoDraftInputs` (frozen dataclass)

Mirrors the `ECOService.create_eco` keyword set **1:1**:
`name, eco_type, product_id, description, priority, user_id,
effectivity_date`. `user_id` keeps `None` as-is — `create_eco` already
normalizes a falsy `user_id` to `1` internally
(`user_id_int = int(user_id) if user_id else 1`), so passing `None` is
correct and preserves the 1:1 mapping. There is no "leave unset".

### 3.3 Functions

- `derive_change_request_reference(intake) -> str` — deterministic
  `sha256` over `(title, change_type, product_id, requester_user_id)`.
  **Recorded only, NOT enforced** — no DB, no dedupe (same deferral as
  the consumption idempotency key).
- `map_change_request_to_eco_draft_inputs(intake) -> EcoDraftInputs` —
  **pure**; does **not** call `create_eco`. The ECO `description` is the
  requester `reason` plus a reserved `[ecr-intake contract_version=…
  reference=…]` envelope (reason-less requests get the envelope alone).
  Does not mutate the intake.

**Envelope is human-readable, NOT a parsing wire format (R1 decision).**
The `[ecr-intake …]` suffix is for operator visibility only. R1 does
**not** commit to it as a stable, parseable format. A future "ECR
persistence" follow-up that needs the reference programmatically MUST
carry it in a structured column, not regex it out of `description`.
This is deliberate: keeping it unstructured avoids locking R1 into a
wire contract before the persistence design exists.

**Reference-determinism invariant.** `derive_change_request_reference`
hashes already-validated, normalized fields (e.g. `change_type` is
lowercased by its validator before it reaches the hash). Any future
field added to the reference material MUST pass through a deterministic
validator first, or the "same logical request → same reference"
guarantee silently breaks. `test_reference_is_deterministic_and_normalisation_stable`
pins the current normalization (`"BOM"`/`" Fix "` → same hash as
`"bom"`/`"Fix"`).

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_ecr_intake_contract.py` (test
groups; counts are a point-in-time snapshot and grow as cases are
added):

- **Intake validation**: minimal valid; title stripped/required;
  `change_type` normalized + unknown rejected fail-fast; `priority`
  default `normal` + unknown rejected; **bom⇒product_id at the intake
  boundary** (non-bom accepted without; bom+product_id ok);
  blank product_id/reason→None; tz-aware `effectivity_date`→naive-UTC;
  frozen + `extra=forbid`.
- **Reference**: deterministic + normalization-stable; differs on each
  stable field; sha256-hex shape.
- **Mapper**: kwargs exactly equal the live `create_eco` parameter set;
  output **binds** to `inspect.signature(ECOService.create_eco)` with
  `user_id=None` *without invoking it*; `user_id` None/None and 7/7
  preserved; description envelope (with/without reason); intake not
  mutated.
- **Purity guard**: AST import scan asserts the module imports nothing
  from `yuantus.database` / `sqlalchemy` / `eco_service` /
  `change_service` / a router / `plugins`, and *does* import
  `yuantus.meta_engine.models.eco` (enum source); a source scan asserts
  `create_eco(` is never called.
- **Drift guards**: `change_type` domain == `{t.value for t in
  ECOType}`; `priority` domain == `{p.value for p in ECOPriority}`;
  `EcoDraftInputs` fields == the `create_eco` parameter set
  (introspected); the bom-invariant constant == `ECOType.BOM.value`.

## 5. Verification Commands

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

Observed as of 2026-05-15: contract tests all passed; doc-index trio
passed; py_compile clean; `git diff --check` clean.

## 6. Non-Goals (reaffirmed from taskbook §6)

The contract does **not** call `ECOService.create_eco`, persist an ECR,
add a route/table/migration/schema, or change `ECOService` /
`ChangeService`. No dedupe enforcement (reference recorded only). No
feature flag. No contact with the workorder version-lock, consumption
MES, pack-and-go, or maintenance bridge contracts. `.claude/` and
`local-dev-env/` stay out of git.

## 7. Follow-ups (each its own separate opt-in)

- **ECR→ECO wiring**: a caller that takes a validated
  `ChangeRequestIntake`, maps it, and actually invokes
  `ECOService.create_eco(**EcoDraftInputs.as_kwargs())` (touches
  DB/permissions).
- **ECR persistence**: an `EngineeringChangeRequest` table + lifecycle
  (intake → triage → spawned-ECO link). Schema change.
- **ECR→ECO dedupe enforcement** using the derived reference.
