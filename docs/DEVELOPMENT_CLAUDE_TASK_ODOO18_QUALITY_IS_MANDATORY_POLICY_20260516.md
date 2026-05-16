# Claude Taskbook: Odoo18 Quality `is_mandatory` Policy Overlay R1

Date: 2026-05-16

Type: **Doc-only taskbook.** Changes no runtime, no schema, no service.
Specifies the contract a later, separately opted-in implementation PR
will deliver. Merging this taskbook does NOT authorize that code.

## 1. Purpose

R2 closeout §4 **Tier-A** follow-up #2 (recommended after ECR dedupe;
lowest-risk tier). The shipped quality↔workorder gate
(`quality_workorder_gate_contract.py`, PR #581 `9545f9f`) treats **every
applicable production point as blocking** because `QualityPoint` has
**no mandatory flag** (ratified §3). This R1 adds a *pure*
caller-supplied **`is_mandatory` policy overlay** so a caller can mark
some points advisory — **without changing the shipped gate, the model,
or any runtime**.

This capability is the one most easily mis-read as a schema/behavior
change, so the boundary below is deliberately strict and test-pinned.

## 2. Current Reality (grounded — read before implementing)

- `src/yuantus/meta_engine/quality/models.py` `QualityPoint` has **no
  `is_mandatory` / `blocking` / `required` column** (confirmed: columns
  are `id, name, title, check_type, product_id, item_type_id,
  routing_id, operation_id, measure_*, worksheet_template,
  instructions, trigger_on, is_active, sequence, properties, …`).
- `src/yuantus/meta_engine/services/quality_workorder_gate_contract.py`
  (merged #581):
  - `QualityPointDescriptor` fields = `id, trigger_on, is_active,
    product_id, item_type_id, routing_id, operation_id` — **all mirror
    `QualityPoint` columns**.
  - `evaluate_operation_quality_gate(facts, points, checks)` —
    **RATIFIED §3**: a point is `blocked`/`missing` (→ `ok=False`)
    unless a scope-matching `pass` check exists. Every applicable
    production point effectively blocks.
  - Pinned by four MANDATORY exactly-named tests + a drift guard
    `test_drift_point_descriptor_fields_subset_of_quality_point_columns`
    asserting `QualityPointDescriptor.model_fields ⊆
    QualityPoint.__table__.columns`.

**The hard constraint (state plainly):** adding `is_mandatory` to the
**existing** `QualityPointDescriptor` would **break** the merged
contract's column-subset drift guard (it is not a `QualityPoint`
column) and would risk altering the ratified §3 behavior. Therefore
`is_mandatory` must NOT be added to the shipped descriptor and the
shipped gate must NOT be modified.

## 3. Ratifiable Decisions (owner/reviewer must ratify before impl)

1. **`is_mandatory` is a caller-supplied policy overlay, not a model
   field.** R1 introduces a **separate** pure structure (proposed:
   `MandatoryPolicy` = an immutable mapping `point_id -> bool`, or a
   small frozen `QualityPointMandatoryEntry`), decoupled from
   `QualityPointDescriptor`. It is **never** a `QualityPoint` column
   and never mirrored by one (the same kind of honest decoupling as the
   `QualityCheck`-has-no-`item_type_id` asymmetry).
2. **Default = mandatory (preserves the shipped ratified §3).** When no
   policy is supplied for a point, that point is treated as
   **mandatory** — i.e. behavior is *identical* to the shipped gate.
   `is_mandatory=False` only ever **downgrades** a point to advisory;
   it can never escalate. (Conservative, mirrors the breakage/quality
   "no silent weakening" stance.)
3. **Additive, parallel function — shipped gate untouched.** R1 adds a
   **new** pure function (proposed:
   `classify_gate_result_by_mandatory(report, policy) ->
   MandatoryGateReport`) that *refines* the existing
   `OperationQualityGateReport` into mandatory-blocking vs advisory.
   `evaluate_operation_quality_gate` and its four MANDATORY tests are
   **not edited** — they must keep passing byte-for-byte.

## 4. R1 Target Output (for the later, separately opted-in impl PR)

New pure module
`src/yuantus/meta_engine/services/quality_mandatory_policy_contract.py`:

- `MandatoryPolicy` — frozen: an immutable, caller-supplied mapping of
  `point_id -> is_mandatory: bool`. Construction from a
  `Mapping[str, bool]`; missing point ⇒ default `True` (decision §3.2).
- `MandatoryGateReport` — frozen dataclass refining the shipped report:
  - `mandatory_blocked: tuple[str, ...]` — blocked/missing points that
    are mandatory under the policy (these are what actually fail).
  - `advisory_unmet: tuple[str, ...]` — blocked/missing points the
    policy marked non-mandatory (informational; do NOT fail).
  - `cleared: tuple[str, ...]` — passthrough of the shipped report's
    cleared points.
  - `mandatory_ok: bool` — `len(mandatory_blocked) == 0`.
- `classify_gate_result_by_mandatory(report: OperationQualityGateReport,
  policy: MandatoryPolicy) -> MandatoryGateReport` — **pure**. Takes the
  **shipped** `evaluate_operation_quality_gate(...)` output and the
  policy; partitions its `blocked + missing` into
  `mandatory_blocked` vs `advisory_unmet` by the policy (default
  mandatory). Does **not** recompute the gate, call the gate, read a
  DB, or raise.

It imports the shipped report **type** only
(`OperationQualityGateReport` from
`quality_workorder_gate_contract`) — it does **not** call
`evaluate_operation_quality_gate` (the caller supplies the already-built
report) and does **not** modify it.

## 5. Tests Required (in the later impl PR)

New `test_quality_mandatory_policy_contract.py`:

- `MandatoryPolicy`: frozen; missing point → default `True`; explicit
  `False` honoured.
- Classification: a blocked point with no policy → `mandatory_blocked`;
  `is_mandatory=False` → `advisory_unmet`, NOT mandatory_blocked;
  `mandatory_ok` reflects only mandatory_blocked; cleared passthrough.
- **`test_default_is_mandatory_preserves_shipped_gate_behavior`
  (MANDATORY, exactly named)** — with an **empty** policy, every
  blocked/missing point in the shipped report is `mandatory_blocked`
  and `mandatory_ok == report.ok`; i.e. no policy ⇒ identical verdict
  to the shipped gate (decision §3.2 pinned).
- **`test_is_mandatory_is_descriptor_only_no_schema_no_runtime`
  (MANDATORY, exactly named)** — asserts (a) `QualityPoint` has no
  `is_mandatory` column; (b) the shipped `QualityPointDescriptor` is
  unchanged (no `is_mandatory` field) so the merged column-subset
  drift guard is unaffected; (c) AST scan: the new module imports
  nothing from `yuantus.database` / `sqlalchemy` / a router / a
  `*_service`, contains no `raise`, and does **not** call
  `evaluate_operation_quality_gate`.
- **`test_shipped_gate_contract_is_untouched` (MANDATORY, exactly
  named)** — imports `quality_workorder_gate_contract` and asserts its
  four MANDATORY test names still exist in
  `test_quality_workorder_gate_contract.py` and
  `QualityPointDescriptor.model_fields` is exactly the merged set (no
  `is_mandatory`).
- Drift/purity guards consistent with the rest of the R2 portfolio;
  the R2 portfolio drift guard
  (`test_odoo18_r2_portfolio_contract.py`) must stay green.

## 6. Verification Commands (for the impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_quality_mandatory_policy_contract.py \
  src/yuantus/meta_engine/tests/test_quality_workorder_gate_contract.py
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
  src/yuantus/meta_engine/services/quality_mandatory_policy_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

## 7. DEV/verification MD requirements (impl PR)

Add `docs/DEV_AND_VERIFICATION_ODOO18_QUALITY_MANDATORY_POLICY_CONTRACT_R1_20260516.md`
+ index registration. It must explicitly document: (a) `is_mandatory`
is a caller policy overlay, NOT a `QualityPoint` column; (b) default =
mandatory ⇒ empty policy is identical to the shipped gate; (c) the
shipped gate + its four MANDATORY tests are untouched; (d) the three
MANDATORY exactly-named tests above.

## 8. Non-Goals (hard boundaries for the impl PR)

- **No `is_mandatory` column / no schema / migration / tenant-baseline.**
- **No edit to the shipped `quality_workorder_gate_contract`** (no new
  field on `QualityPointDescriptor`, no change to
  `evaluate_operation_quality_gate` or its four MANDATORY tests).
- **No enforcement / no `assert_*` / no raiser** — R1 is a pure
  report/classification (a future `assert_mandatory_clear` seam is a
  separate opt-in).
- **No wiring / no runtime / no DB read / no feature flag.**
- No contact with the other R2 contracts beyond importing the shipped
  `OperationQualityGateReport` **type**.
- `.claude/` and `local-dev-env/` stay out of git.

## 9. Decision Gate / Handoff

Doc-only. Implementation owned by Claude Code **only after this
taskbook is merged AND a separate explicit opt-in is given**, on
branch `feat/odoo18-quality-mandatory-policy-contract-r1-20260516`.

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- A `assert_mandatory_clear(...)` enforcement seam (still pure;
  separate so report-vs-enforce stays a conscious choice).
- Modelling `is_mandatory` as a real `QualityPoint` column (schema —
  its own decision, explicitly out of this descriptor-only slice).
- Wiring the classification into any gate caller (depends on the
  non-existent workorder-execution domain — Tier C).

## 10. Reviewer Focus

- Is `is_mandatory` strictly a **caller policy overlay**, never a
  model column, never added to the shipped `QualityPointDescriptor`?
- Does the shipped gate (`evaluate_operation_quality_gate` + its four
  MANDATORY tests + the column-subset drift guard) remain **byte-for-
  byte untouched**, proven by an exactly-named test?
- Is **default = mandatory** (empty policy ⇒ identical verdict to the
  shipped gate) pinned by an exactly-named test?
- Is R1 report-only (no `assert_*`/raise), pure (no DB/runtime,
  doesn't call the gate), and is the R2 portfolio drift guard still
  green?
