# Claude Taskbook: Odoo18 Breakage → ECO Closeout Contract R1

Date: 2026-05-15

Type: **Doc-only taskbook.** Changes no runtime, no schema, no state
machine. Specifies the contract a later, separately opted-in
implementation PR will deliver. Merging this taskbook does NOT authorize
that code.

## 1. Purpose

R2 candidate **breakage → ECO closeout**
(`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md` §四.7). A field
breakage that turns out to be a design defect should loop back into
engineering as a change. Today `BreakageIncident` exists with a status
lifecycle and helpdesk sync, but there is **no path from a breakage to
an engineering change** — the design-loopback is the open gap.

R1 follows the proven contract-first pattern of the six shipped
contracts (workorder version-lock, consumption MES, pack-and-go,
maintenance, ECR intake, automation-rule predicate): a small **pure**
module + tests + DEV/verification MD, default no-op. It **composes with
the already-shipped ECR intake contract** (`ecr_intake_contract.py`, PR
#574, merged `810fd1d`) rather than re-deriving ECO creation.

## 2. Current Reality (grounded — read before implementing)

- `src/yuantus/meta_engine/models/parallel_tasks.py` `BreakageIncident`
  (`meta_breakage_incidents`, class at line 168): `incident_code`,
  `product_item_id`, `bom_id`, `bom_line_item_id`,
  `production_order_id`, `version_id`, `mbom_id`, `routing_id`,
  `batch_code`, `customer_name`, `description` (NOT NULL),
  `responsibility`, `status` (default `"open"`), `severity` (default
  `"medium"`), `created_by_id`.
- `status` vocabulary in practice =
  `{open, in_progress, resolved, closed}` (the value set of
  `BreakageIncidentService._HELPDESK_PROVIDER_TO_INCIDENT_STATUS`,
  ~line 2914). There is **no** status enum class; `status` is a
  free `String(30)`.
- `severity` is a free `String(30)` (default `"medium"`); there is **no
  enum** and no enforced vocabulary anywhere (the service only
  lowercases it for filtering, ~line 3094).
- `BreakageIncidentService` (line 2900): `create_incident(...)` (DB
  write), helpdesk sync, export. There is **no** breakage→ECO /
  breakage→ECR method anywhere; "ECO" never appears in the breakage
  service.
- The **ECR intake contract** already exists and is the right
  downstream: `src/yuantus/meta_engine/services/ecr_intake_contract.py`
  — `ChangeRequestIntake(title, change_type, product_id, priority,
  reason, requester_user_id, effectivity_date)` (Pydantic v2 frozen;
  `change_type` ∈ `ECOType` {bom,product,document}; `priority` ∈
  `ECOPriority` {low,normal,high,urgent}; bom ⇒ product_id) +
  `map_change_request_to_eco_draft_inputs` +
  `derive_change_request_reference`.

**Accurate gap statement.** The data plane (`BreakageIncident`) and the
ECO-intake plane (`ChangeRequestIntake`) both exist; what is missing is
a **typed, pure, testable bridge** from a breakage to a change-request
intake. R1 supplies exactly that bridge — no DB, no state-machine
change, no ECO creation.

## 3. Ratified Design Decisions

Both decisions below are **ratified** by the owner (2026-05-15) — they
are binding contract policy for the implementation PR, **not** open
questions. The impl PR MUST pin each with a directly-named test (see
§5) so the policy cannot be silently changed later.

1. **Eligibility — RATIFIED: `{resolved, closed}`.**
   `is_breakage_eligible_for_design_loopback` returns `True` iff the
   normalized status ∈ `{resolved, closed}`.
   - `open` / `in_progress` are still under triage and must NOT trigger
     a design loopback.
   - `resolved` = investigation concluded; `closed` = process terminal
     state; both are appropriate for the pure "should a change request
     be generated?" layer.
   - **Code-fact support**: in
     `BreakageIncidentService._HELPDESK_PROVIDER_TO_INCIDENT_STATUS`
     (~line 2914) both `resolved` and `closed` are real incident status
     values, and `canceled` maps to `closed` — so restricting to only
     `resolved` would miss terminated-but-closed-out incidents. The
     eligible set must remain a subset of the breakage status
     vocabulary (drift-guarded).
   - Pinned by `test_resolved_and_closed_are_eligible_only`.
2. **severity → ECOPriority — RATIFIED table + `unknown → normal`.**
   `severity` is a free `String(30)` with no enforced vocabulary, so
   fail-fast must NOT block a design loopback. The mapping is
   deterministic and total:
   `critical→urgent`, `high→high`, `medium→normal`, `low→low`;
   **any unrecognized severity → `normal`**.
   - Rationale (ratified): `unknown → normal` is the conservative
     default — it neither escalates dirty data to `urgent`/`high` nor
     drops a breakage that may need engineering attention.
   - This is an **explicitly documented, test-pinned** policy — it must
     never degrade into a "silent default" (the #570 review lesson).
   - Pinned by `test_unknown_severity_maps_to_normal_by_ratified_policy`.

## 4. R1 Target Output (for the later, separately opted-in impl PR)

New pure module, e.g.
`src/yuantus/meta_engine/services/breakage_eco_closeout_contract.py`:

- `BreakageEcoClosureDescriptor` — frozen Pydantic v2,
  `extra="forbid"`. Fields mirror the `BreakageIncident` columns the
  bridge needs: `incident_code`, `product_item_id`, `bom_id`,
  `description` (non-empty), `severity`, `status`, `version_id`
  (carried for traceability). Field names mirror the model so a future
  DB resolver maps 1:1 and a drift test asserts alignment.
- `is_breakage_eligible_for_design_loopback(descriptor) -> bool` —
  pure; `True` iff `status` (normalized lower) ∈ the pinned eligible
  set (§3.1).
- `map_breakage_to_change_request_intake(descriptor) -> ChangeRequestIntake`
  — pure; **reuses the ECR intake contract**. Raises `ValueError` if
  the descriptor is not eligible (caller must check first, or use the
  combined helper). Mapping:
  - `change_type` = `"bom"` if `bom_id` present else `"product"`
    (so bom ⇒ product_id invariant of `ChangeRequestIntake` is
    satisfied by also passing `product_id`; if `bom_id` present but
    `product_item_id` absent, fall back to `"product"` to stay valid —
    pin this edge with a test).
  - `product_id` = `product_item_id`.
  - `title` = a deterministic string from `incident_code` (e.g.
    `"Design loopback: <incident_code or 'breakage'>"`).
  - `reason` = `description` plus a reserved
    `[breakage-eco-closeout contract_version=… incident=… version=…]`
    envelope (human-readable, NOT a parsing wire format — same
    stance as the ECR intake contract; pin in DEV MD).
  - `priority` = severity→ECOPriority per §3.2.
  - `requester_user_id` = None (let `create_eco` default apply, same
    as ECR intake).
- `derive_breakage_change_reference(descriptor) -> str` — deterministic
  sha256 over `(incident_code, product_item_id, version_id)`; recorded
  in the envelope only, **not enforced** (same deferral as the ECR /
  consumption references).

No DB, no `create_eco`, no `BreakageIncident` write, no state-machine
edit. The composed downstream
(`map_change_request_to_eco_draft_inputs`) is already pure and shipped.

## 5. Tests Required (in the later impl PR)

New `test_breakage_eco_closeout_contract.py`:

- Descriptor: frozen, `extra=forbid`, empty `description` rejected,
  blank→None on optionals.
- **`test_resolved_and_closed_are_eligible_only` (MANDATORY, named
  exactly).** Asserts the ratified §3.1 policy: `resolved` and `closed`
  → eligible; `open`, `in_progress`, and any unknown status → NOT
  eligible; case-insensitive. The test name directly expresses the
  ratified decision so a future change to the eligible set breaks a
  test whose name states the policy.
- **`test_unknown_severity_maps_to_normal_by_ratified_policy`
  (MANDATORY, named exactly).** Asserts each ratified §3.2 row
  (`critical→urgent`, `high→high`, `medium→normal`, `low→low`) **and**
  that an unrecognized severity maps to `normal`, with a comment citing
  §3.2 as the ratified, non-silent policy.
- Mapping: `bom_id` present → `change_type="bom"` with
  `product_id=product_item_id`; `bom_id` present but no
  `product_item_id` → `change_type="product"` (pinned edge);
  no `bom_id` → `"product"`; `title`/`reason` envelope; output is a
  valid `ChangeRequestIntake` and round-trips through
  `map_change_request_to_eco_draft_inputs` without error (compose
  proof, no DB).
- Not-eligible descriptor → `map_*` raises `ValueError`.
- `derive_breakage_change_reference` deterministic + differs per stable
  field; sha256-hex.
- Purity guard: AST import scan — module imports nothing from
  `yuantus.database` / `sqlalchemy` / `parallel_tasks_service` / a
  router / `plugins`; it MAY import `ecr_intake_contract` (pure) and
  the ECO model enums.
- Drift guards: descriptor field set ⊆ `BreakageIncident.__table__`
  columns; eligible-status set ⊆ the breakage status vocabulary
  (`BreakageIncidentService._HELPDESK_PROVIDER_TO_INCIDENT_STATUS`
  values, introspected); severity-map codomain ⊆ `ECOPriority` values.

## 6. Verification Commands (for the impl PR)

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

## 7. Non-Goals (hard boundaries for the impl PR)

- **No DB / no `create_eco` / no `BreakageIncident` write / no
  state-machine edit.** The contract is pure and parallel.
- **No change to `BreakageIncidentService`** or the breakage router.
- **No route / table / migration / schema / feature flag.**
- **No dedupe enforcement** (reference recorded only).
- No contact with the workorder version-lock, consumption MES,
  pack-and-go, maintenance, or automation-rule contracts (the ECR
  intake contract is *reused as a pure dependency*, not modified).
- `.claude/` and `local-dev-env/` stay out of git.

## 8. Decision Gate / Handoff

Doc-only. The implementation PR (pure module + tests +
DEV/verification MD) is owned by Claude Code **only after this taskbook
is merged AND a separate explicit opt-in is given**, on branch:

`feat/odoo18-breakage-eco-closeout-contract-r1-20260515`

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- **Breakage→ECR/ECO wiring**: a caller that, when a breakage reaches
  an eligible status, maps it and invokes the ECR intake →
  `create_eco` path (touches DB/permissions/state machine).
- **Breakage state-machine integration** (an explicit "spawn change"
  action / status).
- **Dedupe enforcement** using the derived reference.

## 9. Reviewer Focus

- The two §3 decisions are **ratified, not open** — the reviewer
  verifies *fidelity*, not the choice: is `{resolved, closed}`
  implemented exactly, and is the severity table + `unknown → normal`
  implemented exactly, each pinned by the mandatory exactly-named test
  (`test_resolved_and_closed_are_eligible_only`,
  `test_unknown_severity_maps_to_normal_by_ratified_policy`)?
- Is the contract genuinely pure (no DB/service/router import; reuses
  the ECR intake contract as a pure dependency only)?
- Is the `bom_id`-without-`product_item_id` edge pinned so the produced
  `ChangeRequestIntake` always satisfies its own bom ⇒ product_id
  invariant?
- Do the drift guards introspect the **real** `BreakageIncident`
  columns, breakage status vocabulary, and `ECOPriority` — not
  hard-coded copies?
- Did anything add a route / schema / DB / state-machine edit, or touch
  the prior contracts? It must not.
