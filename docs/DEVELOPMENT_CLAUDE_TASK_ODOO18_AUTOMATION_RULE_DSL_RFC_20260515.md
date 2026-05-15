# Claude Taskbook (RFC): Odoo18 Automation-Rule DSL Evaluation

Date: 2026-05-15

Type: **Doc-only RFC / decision evaluation.** Changes no runtime, no
schema, no rule engine. Output is a recommendation plus a decision gate.
Any code that follows is a separate, independently opted-in
implementation taskbook.

## 1. Purpose

R2 candidate **automation-rule DSL**
(`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md` §3.2
`base_automation` / `plm_workflow_custom_action`). Odoo's
`base_automation` allows arbitrary trigger / condition / action. Yuantus
has a working but **fixed** custom-action engine. The gap analysis and
the owner both flagged this as **RFC-first** — a DSL is a large runtime
surface (parsing, sandboxing, injection, versioning) and must not be
designed prematurely.

This RFC answers one question: **should the rule engine gain a
condition/expression capability, and if so, with what boundary?** It
does not design or implement a DSL.

## 2. Current Reality (grounded)

Evidence (read before forming an opinion):

- `src/yuantus/meta_engine/models/parallel_tasks.py`
  `WorkflowCustomActionRule` (`meta_workflow_custom_action_rules`):
  `name`, `target_object` (default `"ECO"`), `workflow_map_id`,
  `from_state`, `to_state`, `trigger_phase` (`before`/`after`),
  `action_type` (`String(80)` at the DB layer), `action_params`
  (JSON), `fail_strategy` (default `"block"`), `is_enabled`.
  `WorkflowCustomActionRun` records each execution.
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`:
  - `_ALLOWED_TYPES = {"emit_event", "create_job", "set_eco_priority"}`
    — a **fixed 3-action whitelist**. `create_rule`/`update_rule`
    rejects any `action_type` outside it, `trigger_phase` outside
    `{before, after}`, `fail_strategy` outside `{block, warn, retry}`.
  - Matching (`_rule_match_predicates`,
    `_rule_matches_runtime_scope`) is **exact-field equality** on
    `target_object` + `from_state`/`to_state` + `trigger_phase`. There
    is **no condition/expression language** — a rule cannot say "only
    when priority == urgent" or "only if actor in {…}".
- The engine is already wired into ECO transitions (`_run_custom_actions`
  is invoked before/after ECO state moves — see the workorder
  version-lock R1 history).

**Key fact for the decision:** the engine works and is in production
paths. The gap vs. Odoo `base_automation` is **expressiveness** — (a) a
closed 3-action set, and (b) no conditional predicate. The question is
purely whether/how to add conditionality, *not* whether to build a rule
engine.

## 3. The Decision

Should rule matching gain a condition capability beyond exact-field
equality, and should the action set open up — and if so, how, without a
large unsafe runtime surface?

Evaluated against the owner's ordering: **low-risk, default-off,
testable**.

### Option A — Status quo (fixed whitelist, exact-field matching)

Keep the engine exactly as is. New actions / conditions require code +
review each time.

- **Risk**: none.
- **Default-off**: n/a (no change).
- **Testable**: already.
- **Cost**: zero.
- **Downside**: every new automation need is a code change; no
  operator-authored conditionality. The Odoo-parity gap stays open.

### Option B — Declarative predicate, contract-first (recommended slice)

Do **not** add an expression language. Instead define (later, separate
opt-in) a small **pure, declarative** match-predicate contract:
`action_params` (or a sibling field — schema decision deferred) carries
a typed, allow-listed predicate — a fixed operator set
(`eq`/`ne`/`in`/`not_in`) over a fixed, enumerated fact key set
(e.g. `priority`, `eco_type`, `actor_role`). A pure
`evaluate_rule_predicate(predicate, facts) -> bool` is the same proven
shape as the 5 contracts already shipped (consumption MES, pack-and-go,
maintenance, ECR intake): frozen DTO + pure evaluator + drift guards,
**no `eval`, no parser, no DB, no engine wiring**.

- **Risk**: low. Data-only predicate; no code execution; no parser.
- **Default-off**: yes — a rule with no predicate behaves exactly as
  today; the predicate is opt-in per rule.
- **Testable**: high — pure function + drift tests, the exact pattern
  the owner has now validated five times.
- **Cost**: low; one small contract slice. Engine wiring (making the
  matcher actually consult the predicate) is a *separate* later opt-in.
- **Downside**: not a general DSL — bounded operators/keys only. That is
  the point: it closes the "no conditionality" gap at ~80% of the value
  for ~10% of the risk.

### Option C — Sandboxed safe-expression mini-DSL

A constrained expression language, **parsed not `eval`'d** (e.g. an AST
allow-list interpreter).

- **Risk**: medium-high. A parser + sandbox is a real injection /
  resource-exhaustion surface; needs fuzzing, recursion limits,
  versioning of the grammar.
- **Default-off**: gateable, but it is a large new runtime surface.
- **Testable**: large; security tests dominate.
- **Cost**: high; explicitly the "premature DSL" the owner warned
  against.
- **Verdict**: deferred — only revisit if Option B's bounded predicate
  proves insufficient in practice.

### Option D — `eval`/Python-expression DSL

- **Verdict**: **rejected on first principles** — arbitrary code
  execution from operator-authored rules is an unacceptable security
  posture. Not an option.

## 4. Evaluation Summary

| Option | Risk | Default-off | Testable (small) | Closes conditionality gap | Cost |
|---|---|---|---|---|---|
| A status quo | none | n/a | yes | no | zero |
| **B declarative predicate** | **low** | **yes** | **yes** | **mostly** | **low** |
| C sandboxed mini-DSL | med-high | gated | large | yes | high |
| D eval-DSL | unacceptable | — | — | — | — |

## 5. Recommendation

**Adopt Option B as the next slice; Option A as fallback if no
appetite.**

Rationale:

- It is the only option that is simultaneously low-risk, default-off,
  and a genuinely small testable slice — matching the owner's ordering
  and the pattern proven by the five shipped contracts.
- It closes the substantive gap (no operator-authored conditionality)
  without a parser/sandbox.
- It keeps the action set decision orthogonal: widening
  `_ALLOWED_TYPES` is a *separate* small change that does not need a DSL
  and is not bundled here.
- C is deferred (revisit only if B is empirically insufficient); D is
  rejected.

Explicitly **not** recommended now: any expression language, any
`eval`, any change to the live engine in the contract slice, any
schema change.

## 6. Proposed Decision Gate

This RFC authorizes no code. Owner's choice:

1. **Accept Option B** → a separate doc-only implementation taskbook is
   written for "automation-rule declarative predicate contract" (pure
   DTO + `evaluate_rule_predicate` + drift/round-trip tests, no engine
   wiring, no schema), then a separately opted-in implementation PR —
   same doc→impl cadence as the five shipped contracts.
2. **Accept Option A** → record "automation rules stay fixed-action /
   exact-match; conditionality gap accepted" as a closed decision; move
   to the next R2 candidate.
3. **Request deeper analysis** on C (or on the orthogonal
   `_ALLOWED_TYPES` widening) before deciding.

No implementation branch is created until the owner picks 1, 2, or 3.

## 7. Non-Goals (this RFC)

- No code, no engine edit, no parser, no `eval`, no schema, no setting.
- No decision is made *by* this document; it only recommends.
- The `_ALLOWED_TYPES` action-set widening is noted as orthogonal and is
  **not** decided here.
- No contact with the workorder version-lock, consumption MES,
  pack-and-go, maintenance bridge, or ECR intake contracts.
- `.claude/` and `local-dev-env/` stay out of git.

## 8. Reviewer Focus

- Is the "current reality" accurate (fixed 3-action whitelist,
  exact-field matching, no condition language, already ECO-wired)?
  Spot-check `_ALLOWED_TYPES` and the rule-matching predicates.
- Is Option B genuinely free of `eval`/parser (data-only predicate)?
- Is the action-set widening correctly kept orthogonal and undecided?
- Is the decision gate genuinely deferring the code opt-in to the
  owner, and is D unambiguously rejected (not merely discouraged)?
