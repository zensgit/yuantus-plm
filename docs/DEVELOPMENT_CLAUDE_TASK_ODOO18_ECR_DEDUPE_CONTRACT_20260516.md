# Claude Taskbook: Odoo18 ECR Dedupe Pure-Contract R1

Date: 2026-05-16

Type: **Doc-only taskbook.** Changes no runtime, no schema, no service.
Specifies the contract a later, separately opted-in implementation PR
will deliver. Merging this taskbook does NOT authorize that code.

## 1. Purpose

R2 closeout §4 **Tier A** follow-up (recommended next, lowest risk).
The shipped ECR intake contract (`ecr_intake_contract.py`, PR #574,
`810fd1d`) already derives a deterministic
`derive_change_request_reference(intake)` but explicitly **does not
enforce uniqueness** (no dedupe, no DB). This R1 adds the missing
*pure* piece: a **collision report** over a set of change-request
intakes — *report only*, so a future caller can decide what to do.

It is the closest possible extension to the merged ECR intake contract
and composes with it directly (reuses its reference function unchanged).

## 2. Current Reality (grounded — read before implementing)

`src/yuantus/meta_engine/services/ecr_intake_contract.py`:

- `ChangeRequestIntake` (line 54): frozen Pydantic v2 —
  `title`, `change_type`, `product_id`, `priority`, `reason`,
  `requester_user_id`, `effectivity_date`.
- `derive_change_request_reference(intake) -> str` (line 159):
  deterministic `sha256` over
  `(title, change_type, product_id or "", requester_user_id or "")`,
  joined by the module's unit-separator. Its own docstring states it
  is **recorded only, NOT enforced** — there is no dedupe anywhere.
- There is **no** collision/dedupe function in the codebase for change
  requests (grep confirms `derive_change_request_reference` is the only
  reference touchpoint).

**Gap:** two change requests that are logically the same (same
title/change_type/product/requester) derive the **same reference**, but
nothing surfaces that. R1 supplies the pure, testable report. It does
**not** enforce, merge, drop, or persist anything.

## 3. Scope Boundary (read carefully — REPORT ONLY)

Per the owner's explicit instruction, R1 is **report-only**:

- **No enforcement.** There is **no** `assert_*` / raiser in R1
  (deliberately unlike the earlier contracts' assert-seams). The
  function returns a report; the caller decides.
- **No DB, no schema, no migration, no dedupe action** (no merge/drop).
- **`ecr_intake_contract` is reused UNCHANGED** as a pure dependency —
  the reference is *not* reimplemented here (drift-guarded).

## 4. R1 Target Output (for the later, separately opted-in impl PR)

New pure module
`src/yuantus/meta_engine/services/ecr_dedupe_contract.py`:

- `ChangeRequestReferenceCollision` — frozen dataclass:
  `reference: str`, `keys: tuple[str, ...]` (the caller-supplied keys
  of the ≥2 intakes that share this reference).
- `ChangeRequestDedupeReport` — frozen dataclass:
  - `total: int` — number of intakes examined.
  - `unique_references: int` — distinct references.
  - `collisions: tuple[ChangeRequestReferenceCollision, ...]` — only
    references with ≥2 keys, **sorted by `reference`**, each group's
    `keys` in input order (deterministic output).
  - `has_collisions: bool` — `len(collisions) > 0`. (Neutral name —
    this is a *report*, not a gate; no `ok`.)
- `build_change_request_dedupe_report(items) -> ChangeRequestDedupeReport`
  — **pure**. `items` is a `Sequence[tuple[str, ChangeRequestIntake]]`
  (caller key + intake) so the report can name *which* intakes collide
  by the caller's own key, not by opaque index. For each item it calls
  the **imported** `derive_change_request_reference` (reused, not
  reimplemented), groups by reference, and emits a collision per
  reference with ≥2 keys. Duplicate caller keys are allowed (the caller
  owns key semantics); the report does not validate key uniqueness — it
  only groups by reference.

No DB, no `eval`, no enforcement, no `ecr_intake_contract` edit,
no service/router/schema. Caller-supplied items only.

## 5. Tests Required (in the later impl PR)

New `test_ecr_dedupe_contract.py`:

- Empty input → `total=0`, `unique_references=0`, no collisions,
  `has_collisions=False`.
- All-distinct intakes → no collisions; `unique_references == total`.
- Two intakes that derive the same reference (same
  title/change_type/product_id/requester_user_id, differing only in
  `reason`/`priority`/`effectivity_date` — fields NOT in the reference)
  → exactly one collision grouping their two keys.
- A 3-way collision + an unrelated unique → one collision with three
  keys, `unique_references` counted correctly.
- **Determinism**: `collisions` sorted by `reference`; within a group
  `keys` preserve input order; the function is pure (same input →
  identical report).
- **Composition/drift guard**: for every item, the report's reference
  for that item equals
  `ecr_intake_contract.derive_change_request_reference(intake)` — so a
  change to the shipped reference function is reflected, not shadowed.
- **No-enforcement guard**: assert the module exposes **no** callable
  whose name starts with `assert_` and contains no `raise` of a
  dedupe/uniqueness error (AST scan) — R1 is report-only by contract.
- **Purity guard**: AST import scan — module imports nothing from
  `yuantus.database` / `sqlalchemy` / a router / `plugins` / any
  `*_service`; it imports **only**
  `yuantus.meta_engine.services.ecr_intake_contract`
  (`derive_change_request_reference`, `ChangeRequestIntake`).

Doc-index trio stays green for the impl PR's DEV/verification MD.

## 6. Verification Commands (for the impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ecr_dedupe_contract.py \
  src/yuantus/meta_engine/tests/test_ecr_intake_contract.py
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
  src/yuantus/meta_engine/services/ecr_dedupe_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

## 7. DEV/verification MD requirements (impl PR)

The impl PR must add
`docs/DEV_AND_VERIFICATION_ODOO18_ECR_DEDUPE_CONTRACT_R1_20260516.md`
and register it in `docs/DELIVERY_DOC_INDEX.md`. It must explicitly
document: (a) the report-only boundary (no enforcement/DB/schema);
(b) that `ecr_intake_contract` is reused unchanged and the
composition/drift guard pins it; (c) deterministic output ordering.

## 8. Non-Goals (hard boundaries for the impl PR)

- **No enforcement** — no `assert_*`, no raiser, no merge/drop/reject.
- **No DB / schema / migration / tenant-baseline.**
- **No edit to `ecr_intake_contract`** or any service/router.
- No feature flag; no `eval`; no data migration; no runtime wiring.
- No contact with the other R2 contracts.
- `.claude/` and `local-dev-env/` stay out of git.

## 9. Decision Gate / Handoff

Doc-only. The implementation PR (pure module + tests +
DEV/verification MD) is owned by Claude Code **only after this taskbook
is merged AND a separate explicit opt-in is given**, on branch:

`feat/odoo18-ecr-dedupe-contract-r1-20260516`

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- **Dedupe enforcement** (an opt-in caller that rejects/merges on
  collision) — touches DB/permissions; separate.
- **Reference persistence** (storing the reference for cross-request
  dedupe over time) — schema; separate.

## 10. Reviewer Focus

- Is R1 genuinely **report-only** — no `assert_*`/raiser, no
  enforcement path?
- Is `ecr_intake_contract` reused **unchanged** and the reference
  composition pinned by a drift guard (not reimplemented)?
- Is the output deterministic (collisions sorted by reference; keys in
  input order)?
- Is the module pure (imports only `ecr_intake_contract`)?
- Did anything add enforcement / DB / schema, edit the ECR intake
  contract, or touch the other R2 contracts? It must not.
