# Odoo18 R2 Portfolio Closeout — Development and Verification

Date: 2026-05-16

Type: **Doc-only closeout + a read-only portfolio drift guard.** No
runtime, schema, or service change. The portfolio test is pure
introspection (imports + symbol presence + doc/disk consistency) — it
adds no behavior.

## 1. Purpose

Close out the Odoo18 R2 gap-driven cycle (from
`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md`): record what was
delivered, why CAD-conversion-pool is deferred, and the risk-tiered
order for the remaining contract follow-ups — plus a portfolio contract
test so this record cannot silently drift from the codebase.

## 2. Delivered (8 implementations)

All are merged to `main`. The first is a service extension; the other
seven are standalone **pure** contract modules (frozen Pydantic DTOs +
pure functions + drift/purity guards, default-off, no DB).

| # | Capability | PR | Merge commit | Surface |
|---|---|---|---|---|
| 1 | Workorder document version-lock | #565 | `12456d3` | `parallel_tasks_service.WorkorderDocumentPackService` + `parallel_tasks_workorder_docs_router` (**service extension**, not a standalone module) + `meta_workorder_document_links.document_version_id/version_locked_at/version_lock_source` |
| 2 | Consumption ↔ MES ingestion contract | #567 | `6973a4c` | `services/consumption_mes_contract.py` |
| 3 | Pack-and-go version-lock bridge | #570 | `c7e6fd5` | `services/pack_and_go_version_lock_contract.py` |
| 4 | Maintenance ↔ workorder bridge | #572 | `ca6755f` | `services/maintenance_workorder_bridge_contract.py` |
| 5 | ECR intake contract | #574 | `810fd1d` | `services/ecr_intake_contract.py` |
| 6 | Automation-rule predicate (RFC Option B) | #577 | `36ad043` | `services/automation_rule_predicate_contract.py` |
| 7 | Breakage → ECO closeout | #579 | `2775866` | `services/breakage_eco_closeout_contract.py` |
| 8 | Quality ↔ workorder gate | #581 | `9545f9f` | `services/quality_workorder_gate_contract.py` |

### Merged doc-only taskbooks / RFCs

Gap analysis R2 + workorder taskbook (folded into #565's squash);
consumption taskbook #566 `9dd6acc`; pack-and-go mainline RFC #568
`b427d14`; pack-and-go bridge taskbook #569 `9001707`; maintenance
taskbook #571 `02409c5`; ECR taskbook #573 `2b5010f`; automation-rule
DSL RFC #575 `534238f`; automation-rule predicate taskbook #576
`03517a1`; breakage taskbook #578 `a36cddd`; quality taskbook #580
`b3f6671`. (#563/#564 closed superseded — content is on `main` inside
the #565 squash.)

### Cross-cycle invariants that held for all 8

Each split into a doc-only taskbook/RFC PR then a separately-opted-in
implementation PR; each pure module is default-off / behavior-preserving
/ no data migration; each carries an AST purity guard and drift guards
against the real models/enums it mirrors; ratified policy decisions are
pinned by exactly-named MANDATORY tests; nothing is wired into runtime
(every seam is uncalled by design).

## 3. CAD conversion pool multi-server — DEFERRED

The one remaining R2 candidate. **Deferred, not dropped.**

- **Why deferred:** unlike the 8 delivered slices (all expressible as a
  pure, default-off contract), a multi-server CAD conversion pool is
  inherently a **scheduling / concurrency / resource-arbitration**
  problem — server registry, rule-based dispatch, back-pressure,
  failover. It has no honest "pure contract + default-off seam"
  reduction: its value *is* the runtime behavior. Its risk and
  verification surface (timing, contention, partial failure) is the
  largest of the R2 set.
- **Entry conditions (all required before a taskbook is opened):**
  1. An explicit owner opt-in dedicated to it (not bundled).
  2. A concrete operational driver (real multi-server conversion load
     that single-node `file_conversion_router` cannot serve) — not
     speculative.
  3. A decision on whether it composes with the existing P6
     `CircuitBreaker` primitive (reuse vs. new).
  4. A non-prod environment to rehearse concurrency/failover (it cannot
     be validated purely).
- Until then it stays out of scope; this closeout does **not** advance
  it.

## 4. Contract follow-ups — risk tiering & recommended order

None of these are started; each needs its own opt-in. Ordered low→high
risk (continue the proven "lowest-risk-first" cadence):

**Tier A — pure / contract-first (lowest risk; recommended next):**

- `is_mandatory` modelling for the quality gate *as a pure descriptor
  field only* (no schema) — sharpens the gate without runtime.
- ECR intake reference-dedupe *contract* (pure key-collision report) —
  no enforcement, no DB.
- pack-and-go / maintenance / breakage **DB-resolver contracts**
  (pure mapping from already-fetched rows to the existing descriptors,
  caller supplies rows) — extends reach without a DB read in the
  contract.

**Tier B — single, guarded runtime seam wiring (medium; one at a time):**

- automation-rule **engine substitution** — make
  `_rule_matches_runtime_scope` delegate to the merged predicate
  contract. Strongest safety net already exists (the 21-case parity
  matrix is its regression net). Best *first* runtime wiring when the
  owner wants user-visible value; still its own opt-in + its own
  session.

**Tier C — depends on a non-existent substrate (highest; blocked):**

- quality-gate wiring, breakage→ECO wiring, maintenance→mfg wiring:
  each needs an operation/workorder **execution domain that does not
  exist**. These are doubly gated — the execution domain must be built
  (its own large opt-in) before wiring is even meaningful.

**Recommended order:** Tier A (pick one) → optionally one Tier B
(automation engine substitution, dedicated session) → Tier C only after
an execution-domain decision. Do **not** jump to CAD pool or any Tier C
item next.

## 5. Portfolio drift guard

`src/yuantus/meta_engine/tests/test_odoo18_r2_portfolio_contract.py`
(read-only, pure introspection):

- Imports the **7 standalone pure-contract modules** and asserts each
  exposes its documented key public symbols (a rename/removal fails
  loudly here).
- Asserts the workorder version-lock surface
  (`WorkorderDocumentPackService` + the workorder-docs router) still
  exists (the non-module #565 deliverable).
- Asserts **this closeout MD** lists all 8 implementation PR numbers
  and that every `services/*_contract.py` path it cites exists on disk
  — so the closeout cannot drift from reality.

This is the anti-memory-drift mechanism the owner asked for: the
portfolio record is now machine-checked, not just narrated.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_odoo18_r2_portfolio_contract.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
git diff --check
```

No runtime/alembic/tenant-baseline — closeout + read-only test only.

Observed 2026-05-16: portfolio test passed; doc-index trio passed;
`git diff --check` clean.

## 7. Non-Goals

No code/runtime/schema/service change; the portfolio test is pure
introspection. This closeout does not advance CAD pool or any
follow-up — each remains its own explicit opt-in. `.claude/` and
`local-dev-env/` stay out of git.
