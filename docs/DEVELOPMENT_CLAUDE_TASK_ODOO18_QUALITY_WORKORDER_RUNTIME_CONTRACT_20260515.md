# Claude Taskbook: Odoo18 Quality ↔ Workorder Runtime Gate Contract R1

Date: 2026-05-15

Type: **Doc-only taskbook.** Changes no runtime, no schema, no service.
Specifies the contract a later, separately opted-in implementation PR
will deliver. Merging this taskbook does NOT authorize that code.

## 1. Purpose

R2 candidate **quality ↔ workorder runtime**
(`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md` §3.2
`quality_mrp_workorder*`). Odoo enforces in-process quality checks at
work-order steps. Yuantus has the *data* linkage
(`QualityPoint`/`QualityCheck` carry `routing_id`/`operation_id`) but
no mechanism that decides "is this operation quality-clear?".

## 2. Current Reality (grounded — read before implementing; this is honest, not aspirational)

- `src/yuantus/meta_engine/quality/models.py`:
  - `QualityPoint` (`meta_quality_points`, line 71): `check_type`,
    `product_id`, `item_type_id`, `routing_id`, `operation_id`,
    measure bounds, `worksheet_template`, **`trigger_on`** (line 107,
    default `"manual"`; vocabulary `{manual, receipt, production,
    transfer}`), `is_active`, `sequence`. **There is NO
    `is_mandatory` / `blocking` / `required` flag.**
  - `QualityCheck` (`meta_quality_checks`, line 127): `point_id`,
    `product_id`, `routing_id`, `operation_id`, `check_type`,
    `result` (`QualityCheckResult`: `none|pass|fail|warning`),
    `source_document_ref`, `lot_serial`, `checked_at`.
  - Enums: `QualityCheckType` {pass_fail, measure, take_picture,
    worksheet, instructions}; `QualityCheckResult` {none, pass, fail,
    warning}.
- **`trigger_on` is a dormant field.** `grep` shows it is only
  *stored and validated* (`quality/service.py:55`) and *echoed back*
  (`quality/service.py:376`, `quality_common.py:78`). **Nothing
  consumes `trigger_on` for any runtime decision anywhere.**
- **There is NO operation / workorder execution runtime.**
  `manufacturing/models.py` `Operation` (line 118) has `run_time` /
  `labor_run_time` / `sequence` / `workcenter_id` but **no
  state/status/start/complete lifecycle**. `manufacturing_router.py`
  is BOM/routing/operation **CRUD + MBOM release** only — there is no
  start/complete/run-operation endpoint, and no MES workorder-instance
  domain (consistently a non-goal across this cycle).
- `QualityService` (line 21): `create_point`, `list_points`,
  `create_check`, `record_check_result`, `create_alert`,
  `transition_alert`, `get_alert_manufacturing_context`. No
  operation-gate method exists.

**Honest consequence (state this plainly; do not paper over it).**
There is **no live "operation runs" event to hook**. So "quality →
workorder *runtime*" cannot, in R1, mean "block operation completion" —
that completion path does not exist. R1's minimal slice is therefore a
**pure quality-gate contract + a default-OFF enforcement seam** that
*activates the dormant `trigger_on="production"` semantics in a pure,
testable form*. True runtime enforcement is a separate, later opt-in
that is itself **blocked on a workorder-execution domain that does not
exist** (so it is doubly gated). This honesty is deliberate — see the
automation-rule RFC lesson (do not claim a runtime hook that is not
there).

## 3. Ratified Decision

Because `QualityPoint` has **no mandatory/blocking flag**, the gate's
"what blocks an operation" is a pinned policy, not invented silently.

**RATIFIED by the owner (2026-05-15) — binding, test-pinned, not an
open question:** an operation is *quality-clear* iff **every applicable
`QualityPoint` (see §4 scope rule) has at least one *scope-matching*
`QualityCheck` with `result == "pass"`.** A point with only
`fail` / `warning` / `none` / missing scope-matching checks → operation
**blocked**. **`warning` does NOT clear** the gate (ratified
conservative policy — there is no mandatory flag and R1 is default-off,
so the conservative choice cannot affect production behavior but
prevents a future wiring from treating a quality `warning` as
pass-through). Non-`production` `trigger_on` points are out of scope.
Pinned by the four MANDATORY exactly-named tests in §5 (incl. the scope tests).

## 4. R1 Target Output (for the later, separately opted-in impl PR)

New pure module
`src/yuantus/meta_engine/services/quality_workorder_gate_contract.py`.

### 4.1 Scope model (the four-field wildcard rule)

`QualityPoint` carries **four** scope fields — `product_id`,
`item_type_id`, `routing_id`, `operation_id` — not two. `QualityCheck`
carries only **three** — `product_id`, `routing_id`, `operation_id`
(**there is NO `item_type_id` on `QualityCheck`** — this asymmetry is
real and must be modeled honestly, not invented).

**Scope-match rule (applied identically for point applicability and
for check-to-facts matching):** for each scope field, the descriptor
matches the facts iff the descriptor field is `None` (**wildcard**) or
**equals** the corresponding facts field. A point uses all four fields;
a check uses its three (`item_type_id` is simply not a check
constraint).

### 4.2 DTOs

- `OperationQualityFacts` — frozen Pydantic v2, `extra="forbid"`: the
  operation context the caller resolved — `product_id`,
  `item_type_id`, `routing_id`, `operation_id` (all optional).
- `QualityPointDescriptor` — frozen: `id`, `product_id`,
  `item_type_id`, `routing_id`, `operation_id`, `trigger_on`,
  `is_active`. Field names mirror `QualityPoint` (drift-guarded).
- `QualityCheckDescriptor` — frozen: `point_id`, `result`,
  **`product_id`, `routing_id`, `operation_id`** (the check's own
  scope — NO `item_type_id`, mirroring the model). `result` validated
  against the live `QualityCheckResult` domain.

### 4.3 Pure functions

- `resolve_applicable_quality_points(facts, points) -> tuple[...]` —
  the points that are `is_active` **and** `trigger_on=="production"`
  **and** whose **four-field scope** matches `facts` per §4.1. This
  activates the dormant `trigger_on="production"` meaning.
- `evaluate_operation_quality_gate(facts, points, checks)
  -> OperationQualityGateReport` — pure, never raises. A point is
  *cleared* iff there exists a check with `check.point_id == point.id`
  **AND** `check.result == "pass"` **AND** the **check's three-field
  scope matches `facts`** per §4.1. This per-check scope filter is the
  fix for cross-product / cross-routing / cross-operation
  contamination: a `pass` check that belongs to a different
  product/routing/operation context **must not** clear the current
  operation's point even if `point_id` coincides. Report:
  `total / blocked / missing / cleared` lists + `ok: bool`
  (`ok` iff `blocked` and `missing` are both empty).
- `assert_operation_quality_clear(facts, points, checks) -> None` —
  the **enforcement seam**: raises `ValueError` listing offending
  point ids when not `ok`; `None` when clear. **Default-OFF by
  construction** — nothing in the codebase calls it (there is no
  operation-completion path), so merging R1 changes no behavior.

No DB, no `eval`, no engine wiring, no quality/manufacturing
service/model/router edit. Caller-supplied descriptors only; a DB
resolver is a separate opt-in.

## 5. Tests Required (in the later impl PR)

New `test_quality_workorder_gate_contract.py`:

- DTO validation: frozen, `extra=forbid`; `QualityCheckDescriptor.result`
  rejects values outside `QualityCheckResult`.
- Resolver: only `is_active` + `trigger_on=="production"` points;
  non-production / inactive excluded.
- **`test_point_four_field_scope_wildcard_and_equality`
  (MANDATORY, exactly named)** — pins §4.1 for points: each of
  `product_id` / `item_type_id` / `routing_id` / `operation_id` —
  `None` on the point = wildcard (matches); non-`None` must equal the
  facts field, else the point does NOT apply. Includes a case where a
  production point for a *different* `product_id` and one for a
  different `item_type_id` are correctly excluded.
- **`test_cross_scope_pass_check_does_not_clear`
  (MANDATORY, exactly named)** — pins §4.3: a `pass` check whose
  `point_id` matches but whose `product_id` / `routing_id` /
  `operation_id` differs from the facts must NOT clear the point
  (cross-product / cross-routing / cross-operation contamination
  guard); a check for a different `point_id` must NOT clear either.
- **`test_only_production_trigger_points_gate_the_operation`
  (MANDATORY, exactly named)** — pins that `manual`/`receipt`/
  `transfer` points never block an operation.
- **`test_pass_clears_fail_warning_none_block_by_ratified_policy`
  (MANDATORY, exactly named)** — pins the §3 ratified gate: `pass`
  clears; `fail`/`warning`/`none`/missing block; **`warning` does NOT
  clear**; comment cites §3 as the ratified policy.
- Gate: empty applicable set → `ok=True` (no production points = not
  gated); mixed; `assert_*` raises listing offending ids / returns
  None when clear.
- Purity guard: AST import scan — module imports nothing from
  `yuantus.database` / `sqlalchemy` / `quality.service` /
  `manufacturing` / a router / `plugins`; MAY import the quality
  model enums only.
- Drift guards: descriptor field sets ⊆ `QualityPoint` /
  `QualityCheck` `__table__` columns; the gate's accepted `result`
  domain == `{r.value for r in QualityCheckResult}`; the production
  trigger literal `"production"` ∈ the `trigger_on` vocabulary
  validated in `quality/service.py` — introspected so a change fails
  loudly.

Doc-index trio stays green for the impl PR's DEV/verification MD.

## 6. Verification Commands (for the impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_quality_workorder_gate_contract.py \
  src/yuantus/meta_engine/tests/test_quality_service.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/quality_workorder_gate_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

## 7. DEV/verification MD requirements (impl PR)

The impl PR must add
`docs/DEV_AND_VERIFICATION_ODOO18_QUALITY_WORKORDER_GATE_CONTRACT_R1_20260515.md`
and register it in `docs/DELIVERY_DOC_INDEX.md`. It must explicitly
document: (a) the §3 ratified gate policy and the four MANDATORY test
names; (b) the honest finding that no operation-execution runtime
exists, so the seam is default-off and true enforcement is gated on a
future workorder-execution domain; (c) the contract is pure/parallel,
no behavior change, no data migration.

## 8. Non-Goals (hard boundaries for the impl PR)

- **No operation/workorder execution runtime** (it does not exist;
  R1 does not create one).
- **No wiring** of the seam into any path; no setting that defaults on.
- **No edit** to `QualityService`, `QualityPoint`/`QualityCheck`
  models, manufacturing services, or any router.
- **No `is_mandatory` column** or any schema/migration/tenant-baseline.
- No DB read in the contract; a DB resolver is a separate opt-in.
- No feature flag; no `eval`; no data migration.
- No contact with the prior seven Odoo18 contracts.
- `.claude/` and `local-dev-env/` stay out of git.

## 9. Decision Gate / Handoff

Doc-only. The implementation PR (pure module + tests +
DEV/verification MD) is owned by Claude Code **only after this taskbook
is merged AND a separate explicit opt-in is given**, on branch:

`feat/odoo18-quality-workorder-gate-contract-r1-20260515`

Follow-ups, each its own separate opt-in (explicitly NOT in R1, and
the first is itself blocked on a non-existent substrate):

- **Workorder-execution domain** (operation start/complete lifecycle) —
  prerequisite for any real runtime enforcement; does not exist today.
- **Gate wiring**: a future operation-completion path calling
  `assert_operation_quality_clear` (depends on the above).
- **`is_mandatory` modelling** if per-point blocking granularity is
  later wanted (schema change).

## 10. Reviewer Focus

- Is the "current reality" honest and accurate — `trigger_on` dormant,
  **no** operation-execution runtime, no mandatory flag? Spot-check
  `quality/service.py:55`, `manufacturing/models.py:118`,
  `manufacturing_router.py`.
- The §3 gate policy is **ratified, not open** — verify *fidelity*:
  `pass` clears, `fail`/`warning`/`none`/missing block, `warning` does
  NOT clear, pinned by the four MANDATORY exactly-named tests.
- **Scope correctness (the #580 review fix):** are all four point
  scope fields (`product_id`, `item_type_id`, `routing_id`,
  `operation_id`) honoured with the None=wildcard / non-None=equal
  rule, and does the per-check three-field scope filter prevent a
  cross-product / cross-routing / cross-operation `pass` from clearing
  the wrong point? Is the `QualityCheck`-has-no-`item_type_id`
  asymmetry modeled honestly (not invented onto the check)?
- Is the seam genuinely default-OFF (nothing calls it; no path exists)
  and the contract pure (no service/model/router/DB import)?
- Do the drift guards introspect the **real** `QualityPoint`/
  `QualityCheck` columns, `QualityCheckResult`, and the `trigger_on`
  vocabulary — not hard-coded copies?
- Did anything add a runtime path / schema / wiring, or touch the
  prior contracts? It must not.
