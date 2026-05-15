# Claude Taskbook (RFC): Odoo18 Automation-Rule Predicate Evaluation

Date: 2026-05-15 (R2 — premise corrected per #575 review)

Type: **Doc-only RFC / decision evaluation.** Changes no runtime, no
schema, no rule engine. Output is a recommendation plus a decision gate.
Any code that follows is a separate, independently opted-in
implementation taskbook.

> **Correction (R2).** The first draft of this RFC asserted "no
> condition/expression language exists". That was **wrong** — review
> found a working, validated, runtime-consulted `match_predicates`
> facility already embedded in `WorkflowCustomActionService`. This
> revision restates the current reality accurately and reframes the
> decision from "introduce conditionality" to "what to do with the
> conditionality that already exists".

## 1. Purpose

R2 candidate **automation-rule DSL**
(`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md` §3.2
`base_automation` / `plm_workflow_custom_action`). The owner flagged
this RFC-first to avoid prematurely building DSL runtime.

This RFC answers: **the rule engine already has a bounded predicate
facility embedded in a DB-bound service — should it be formalized as a
pure contract, have its operators/keys extended, or be left as-is?** It
does not design or implement a DSL.

## 2. Current Reality (grounded, corrected)

Evidence (read before forming an opinion):

- `src/yuantus/meta_engine/models/parallel_tasks.py`
  `WorkflowCustomActionRule`: `name`, `target_object` (default
  `"ECO"`), `workflow_map_id`, `from_state`, `to_state`,
  `trigger_phase` (`before`/`after`), `action_type`, `action_params`
  (JSON), `fail_strategy`, `is_enabled`.
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
  `WorkflowCustomActionService`:
  - **Fixed 3-action whitelist**: `_ALLOWED_TYPES =
    {emit_event, create_job, set_eco_priority}` (line 2006).
  - **Conditionality already exists.** `_ALLOWED_MATCH_PREDICATES =
    {stage_id, eco_priority, actor_roles, product_id, eco_type}`
    (line 2009). `_normalize_match_predicates` (line 2112) validates
    them (`eco_priority ∈ {low,normal,high,urgent}`, `eco_type ∈
    {bom,product,document}`, `actor_roles` a string list, ids
    normalized). `create_rule` (line 2275) accepts a `match_predicates=`
    argument and stores it under
    `action_params["match_predicates"]`.
  - **It is consulted at runtime.** `_rule_matches_runtime_scope`
    (line 2195) evaluates predicates against a runtime context:
    **equality** for `stage_id` / `eco_priority` / `product_id` /
    `eco_type`, and **set-intersection** for `actor_roles`. A rule
    whose predicate does not match the transition context is skipped.
  - `evaluate_transition` (line 2363) drives this and is wired into ECO
    transitions via `eco_service.py:243`
    (`WorkflowCustomActionService(...).evaluate_transition(...)`).
  - Tests already exercise it
    (`test_parallel_tasks_services.py` ~lines 1276/1321 around
    `evaluate_transition` with predicates).

**Accurate gap statement.** Conditionality is **not absent** — it is:

1. **Embedded** in the DB-bound `WorkflowCustomActionService` (cannot be
   unit-tested or reused in isolation; no pure surface).
2. **Operator-fixed**: only equality (and `actor_roles` intersection).
   No `ne` / `in` / `not_in` / range / negation.
3. **Key-fixed**: exactly the 5 allow-listed predicate keys.

The action-set (`_ALLOWED_TYPES`) is a separate, orthogonal concern and
is **not** decided here.

## 3. The Decision

Given that a bounded predicate facility already exists embedded in the
service, what — if anything — should change, judged against the owner's
ordering (**low-risk, default-off, testable**)?

### Option A — Leave as-is

Keep `match_predicates` exactly where and how it is.

- **Risk**: none.
- **Testable**: only via the DB-bound service (no isolated unit
  surface).
- **Cost**: zero.
- **Downside**: the predicate logic stays untestable in isolation and
  un-reusable; any future refactor of `WorkflowCustomActionService`
  risks silently changing matching semantics with no behavior-pinning
  guard.

### Option B — Formalize the existing predicate as a pure contract (recommended)

Do **not** change runtime behavior. Extract the *exact* current
semantics of `_rule_matches_runtime_scope` into a small **pure**
contract (frozen predicate DTO + frozen facts DTO +
`evaluate_rule_predicate(predicate, facts) -> bool`) that reproduces
equality-for-4-keys + actor-role-intersection **bit-for-bit**, plus a
**compatibility/drift guard** asserting the pure contract and the
embedded service agree on a matrix of cases (and that the pure
predicate-key set tracks `_ALLOWED_MATCH_PREDICATES`). Same proven shape
as the five shipped contracts (consumption MES, pack-and-go,
maintenance, ECR intake): pure DTO + evaluator + drift tests, no DB, no
engine wiring, no behavior change.

- **Risk**: low. Behavior-preserving; the service keeps its own code in
  R1 (the contract is parallel, not yet substituted). No `eval`, no
  parser, no schema.
- **Default-off**: yes — nothing calls the contract in production until
  a *separate* opt-in swaps the service to delegate to it.
- **Testable**: high — pure function + a compat matrix that pins the
  current semantics so a later refactor cannot drift silently.
- **Cost**: low; one small contract slice.
- **Downside**: does not by itself add operators/keys — deliberately.
  It makes the existing behavior safe to evolve first.

### Option C — Extend operators / keys

Add `ne` / `in` / `not_in` (and/or new fact keys) to the predicate.

- **Risk**: medium. Touches live matching semantics; needs careful
  back-compat (existing rules must behave identically).
- **Verdict**: **deferred** — and explicitly *easier and safer after
  Option B*, because the compat guard from B is exactly what makes an
  operator extension verifiable. Revisit as its own taskbook once B
  exists.

### Option D — `eval` / expression-language DSL

- **Verdict**: **rejected on first principles** — operator-authored
  arbitrary code execution is an unacceptable security posture.

## 4. Evaluation Summary

| Option | Risk | Default-off | Testable (small) | Value | Cost |
|---|---|---|---|---|---|
| A leave as-is | none | n/a | only via DB service | none | zero |
| **B formalize as pure contract** | **low** | **yes** | **yes** | **makes existing behavior safe to evolve** | **low** |
| C extend operators/keys | medium | gated | medium | higher expressiveness | medium (safer after B) |
| D eval-DSL | unacceptable | — | — | — | — |

## 5. Recommendation

**Adopt Option B as the next slice; Option A as fallback if no
appetite.**

Rationale:

- The conditionality already exists but is **untestable in isolation
  and unguarded against refactor drift**. B closes that without
  changing a single runtime behavior — the lowest-risk way to make the
  feature evolvable.
- It is the same pure-contract shape the owner has validated five times.
- It makes Option C (operator/key extension) materially safer later,
  because B's compat guard becomes the regression net for any semantic
  change.
- C is deferred to its own opt-in; D is rejected; the `_ALLOWED_TYPES`
  action-set widening remains orthogonal and undecided.

Explicitly **not** recommended now: any operator/key change, any
`eval`/parser, any edit to the live `WorkflowCustomActionService`
matching code in the contract slice, any schema change.

## 6. Proposed Decision Gate

This RFC authorizes no code. Owner's choice:

1. **Accept Option B** → a separate doc-only implementation taskbook
   for "automation-rule predicate pure-contract + service-parity guard"
   (pure DTO + `evaluate_rule_predicate` + a compat matrix vs
   `_rule_matches_runtime_scope`, no engine edit, no schema), then a
   separately opted-in implementation PR — same doc→impl cadence as the
   five shipped contracts.
2. **Accept Option A** → record "match_predicates stays embedded;
   isolation/drift-guard gap accepted" as a closed decision; move on.
3. **Request deeper analysis** on C (operator/key extension) or on the
   orthogonal `_ALLOWED_TYPES` widening before deciding.

No implementation branch is created until the owner picks 1, 2, or 3.

## 7. Non-Goals (this RFC)

- No code, no engine edit, no parser, no `eval`, no schema, no setting.
- No decision is made *by* this document; it only recommends.
- The `_ALLOWED_TYPES` action-set widening and the Option C operator/key
  extension are noted as separate and are **not** decided here.
- No contact with the workorder version-lock, consumption MES,
  pack-and-go, maintenance bridge, or ECR intake contracts.
- `.claude/` and `local-dev-env/` stay out of git.

## 8. Reviewer Focus

- Is the corrected "current reality" accurate — `match_predicates`
  exists (`_ALLOWED_MATCH_PREDICATES` line 2009), is validated
  (`_normalize_match_predicates` line 2112), is runtime-consulted
  (`_rule_matches_runtime_scope` line 2195 / `evaluate_transition` line
  2363), and is ECO-wired (`eco_service.py:243`)?
- Is Option B genuinely behavior-preserving (a *parallel* pure contract
  + compat guard, not a rewrite of the live matcher) and free of
  `eval`/parser?
- Are Option C (operators/keys) and the `_ALLOWED_TYPES` widening
  correctly kept separate and undecided?
- Is the decision gate genuinely owner-deferred and is D unambiguously
  **rejected**?
