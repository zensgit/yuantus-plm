# Claude Taskbook: Odoo18 Automation-Rule Predicate Pure-Contract R1

Date: 2026-05-15 (R2 — interface + workflow_map_id scope aligned to the owner's development plan)

Type: **Doc-only taskbook.** Changes no runtime, no schema, no rule
engine. Specifies the contract a later, separately opted-in
implementation PR will deliver. Merging this taskbook does NOT authorize
that code.

> **Revision note (R2).** The first draft excluded `workflow_map_id`
> from the contract and used a `workflow_map_id=None` parity workaround.
> The owner's development plan instead **includes `workflow_map_id`** in
> the contract (it is part of `_rule_matches_runtime_scope` and the
> contract should reproduce the *full* match decision). This revision
> aligns the interface names and the scope accordingly.

## 1. Purpose

Implements the **Option B** decision from the automation-rule RFC
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_AUTOMATION_RULE_DSL_RFC_20260515.md`,
merged `534238f`): the rule-matching logic already exists but is
**embedded** in the DB-bound `WorkflowCustomActionService` with no
isolated, testable, refactor-safe surface. R1 extracts its **exact
current semantics** into a small **pure** contract plus a
**service-parity compat matrix** — *behavior-preserving*, no engine
edit, no schema, no `eval`/parser.

R1 follows the proven contract-first pattern of the five shipped
contracts (workorder version-lock, consumption MES, pack-and-go,
maintenance, ECR intake): pure DTO + pure evaluator + drift/parity
tests, default no-op. Claude owns PR 1 (this doc) and PR 2
(implementation); Codex does independent review and merge verification;
no auto-merge.

## 2. Current Reality (grounded — read before implementing)

`src/yuantus/meta_engine/services/parallel_tasks_service.py`,
`WorkflowCustomActionService`:

- `_ALLOWED_MATCH_PREDICATES` (line 2009) = `{stage_id, eco_priority,
  actor_roles, product_id, eco_type}`.
- `_normalize_match_predicates` (line 2112): `stage_id`/`product_id` →
  optional trimmed string; `eco_priority` → lowercased, must be
  `{low,normal,high,urgent}`; `eco_type` → lowercased, must be
  `{bom,product,document}`; `actor_roles` → de-duplicated lowercased
  string list; unknown keys / bad enum / non-array `actor_roles` /
  non-dict → `ValueError`; empties dropped.
- `_rule_match_predicates` (line 2169): reads
  `rule.action_params["match_predicates"]`, calls
  `_normalize_match_predicates`, and **on `ValueError` returns `{}`** →
  **fail-open** (illegal stored predicate ⇒ "match everything").
- `_normalize_runtime_context` (line 2177): normalizes runtime facts
  identically (lowercase `eco_priority`/`eco_type`, optional strings,
  lowercased `actor_roles` list, plus `workflow_map_id` optional
  string).
- `_rule_matches_runtime_scope` (line 2195), in order:
  1. `workflow_map_id = _normalize_optional_string(rule.workflow_map_id)`
     (a **rule column**, read *before* and independent of the
     predicate fail-open path): if truthy and `!=
     context["workflow_map_id"]` → `False`.
  2. effective predicate = `_rule_match_predicates(rule)` (fail-open).
  3. `stage_id`: if predicate value truthy and `!=
     context["stage_id"]` → `False`.
  4. `eco_priority`: same pattern.
  5. `product_id`: same pattern.
  6. `eco_type`: same pattern.
  7. `actor_roles`: if predicate list non-empty and
     `set(context.actor_roles) ∩ predicate.actor_roles == ∅` → `False`.
  8. else `True`.
  Each scalar check is **"only enforced if the value is truthy"** — an
  absent value is a wildcard.
- Wired into ECO transitions via `eco_service.py:243`.
- Existing tests:
  `test_workflow_custom_actions_match_runtime_scope_predicates`
  (`test_parallel_tasks_services.py` ~line 1400),
  `test_workflow_custom_actions_match_context_predicates` (~line 1525),
  and the router test
  `test_parallel_tasks_router.py::test_workflow_rule_upsert_accepts_match_predicates`
  (~line 2057).

**Key fact:** `workflow_map_id` is a *rule column* read at step 1,
**before** and independent of the predicate fail-open path — so an
illegal stored `match_predicates` zeroes only the predicate keys while
`workflow_map_id` still applies. The contract must model this exactly.

## 3. Scope

The pure contract reproduces the **full** `_rule_matches_runtime_scope`
match decision: step 1 (`workflow_map_id`) **and** steps 3–8 (the 5
`_ALLOWED_MATCH_PREDICATES` keys), including the fail-open derivation.

`workflow_map_id` is carried as a **separate constructor input**
(not part of `match_predicates`) so that the fail-open path zeroes only
the predicate-derived keys while `workflow_map_id` survives —
bit-for-bit with the service. Because the contract now covers the full
decision, the parity matrix compares directly against
`_rule_matches_runtime_scope` with **`workflow_map_id` varied** (no
`workflow_map_id=None` workaround).

## 4. R1 Target Output (for the later, separately opted-in impl PR)

New pure module
`src/yuantus/meta_engine/services/automation_rule_predicate_contract.py`:

- `WorkflowRulePredicate` — frozen Pydantic v2, `extra="forbid"`.
  Fields (all optional, absent = wildcard): `workflow_map_id`,
  `stage_id`, `eco_priority`, `actor_roles` (tuple),
  `product_id`, `eco_type`. Validation **mirrors**
  `_normalize_match_predicates` for the 5 predicate keys (enum domains
  for `eco_priority`/`eco_type`, lowercasing, de-dup, empties→absent);
  `workflow_map_id` is an optional trimmed string (mirrors
  `_normalize_optional_string`).
- `WorkflowRuleFacts` — frozen Pydantic v2: the runtime-context
  counterpart (`workflow_map_id`, `stage_id`, `eco_priority`,
  `product_id`, `eco_type`, `actor_roles`), normalized exactly like
  `_normalize_runtime_context`.
- `normalize_workflow_rule_predicate(workflow_map_id, match_predicates)
  -> WorkflowRulePredicate` — pure mirror of `rule.workflow_map_id` +
  `_rule_match_predicates`: normalize `workflow_map_id` independently;
  normalize `match_predicates`; **on any `match_predicates` validation
  error, degrade to the empty predicate but PRESERVE the normalized
  `workflow_map_id`** (bit-for-bit fail-open). Raises nothing.
- `evaluate_rule_predicate(predicate, facts) -> bool` — pure mirror of
  steps 1 + 3–8: `workflow_map_id` truthy-exact; `stage_id` /
  `eco_priority` / `product_id` / `eco_type` truthy-exact;
  `actor_roles` lowercase set-intersection; absent = wildcard; empty
  predicate (and no `workflow_map_id`) → `True`.

No DB, no `eval`, no parser, no engine wiring, no behavior change. The
service keeps its own code in R1 (the contract is **parallel**, not yet
substituted — substitution is a separate opt-in).

Also add
`docs/DEV_AND_VERIFICATION_ODOO18_AUTOMATION_RULE_PREDICATE_CONTRACT_R1_20260515.md`
and register it in `docs/DELIVERY_DOC_INDEX.md`.

## 5. Tests Required (in the later impl PR)

New `test_automation_rule_predicate_contract.py`:

- DTO: frozen, `extra="forbid"`, normalization, blank→absent,
  `actor_roles` de-dup/lowercase, unknown `eco_priority`/`eco_type`
  rejected.
- Evaluator matrix: empty predicate → always `True`; each single key
  match/mismatch (truthy-equality); `actor_roles` intersection (match
  iff overlap); multi-key AND; absent key = wildcard.
- `workflow_map_id`: matches **independently** of `match_predicates`
  (set workflow_map_id only → enforced; with predicates → both AND).
- **Fail-open pin**: each illegal stored `match_predicates`
  (unsupported key, bad `eco_priority`/`eco_type`, non-array
  `actor_roles`, non-dict) → `normalize_workflow_rule_predicate`
  yields the empty predicate **but keeps `workflow_map_id`**, and
  `evaluate_rule_predicate` then matches all facts that satisfy
  `workflow_map_id` — asserted with a comment citing
  `_rule_match_predicates` line 2169 as the pinned behavior.
- **Service-parity matrix** (core R1 value): a table of
  `(workflow_map_id, raw_match_predicates, runtime_context)` cases —
  legal, empty, wildcard, multi-key, actor-role, **illegal/fail-open**,
  and `workflow_map_id` set/unset — each asserted to produce the
  **same boolean** from (a) the real
  `WorkflowCustomActionService._rule_matches_runtime_scope`, and (b)
  `evaluate_rule_predicate(normalize_workflow_rule_predicate(...),
  WorkflowRuleFacts(**ctx))`. A real cross-check, not a tautology.
- Purity guard: AST import scan asserts the **module** imports nothing
  from `yuantus.database` / `sqlalchemy` / a router / the
  `WorkflowCustomActionService`; enum domains, if needed, come from the
  model layer. The parity *test* may import the service; the *module*
  must not.
- Drift guard: the contract's predicate-key set ==
  `WorkflowCustomActionService._ALLOWED_MATCH_PREDICATES`; the
  `eco_priority`/`eco_type` domains == the service's
  `_ALLOWED_ECO_PRIORITIES`/`_ALLOWED_ECO_TYPES` (introspected — a
  change on either side fails loudly).

## 6. Verification Commands (for the impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_automation_rule_predicate_contract.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/automation_rule_predicate_contract.py
git diff --check
```

No alembic / tenant-baseline — the contract adds no schema.

## 7. Non-Goals (hard boundaries for the impl PR)

- **No service edit / no router edit.** `WorkflowCustomActionService`,
  `_rule_matches_runtime_scope`, `_rule_match_predicates`, and the
  parallel-tasks router are **not** modified; the contract is parallel
  only. Substituting the service to delegate to the contract is a
  **separate** opt-in.
- **No operator/key extension** (`ne`/`in`/`not_in`/new keys) — RFC
  Option C, separate opt-in.
- **No fail-open → fail-closed hardening** — separate opt-in; R1
  *pins* fail-open, it does not change it.
- **No `_ALLOWED_TYPES` action-set widening** — orthogonal, undecided.
- No route / table / migration / schema / DB read / feature flag /
  `eval` / parser / runtime wiring.
- No contact with the workorder version-lock, consumption MES,
  pack-and-go, maintenance bridge, or ECR intake contracts.
- `.claude/` and `local-dev-env/` stay out of git.

## 8. Decision Gate / Handoff

Doc-only. The implementation PR is owned by Claude Code **only after
this taskbook is merged AND a separate explicit opt-in is given**, on
branch:

`feat/odoo18-automation-rule-predicate-contract-r1-20260515`

Codex reviews each PR independently and verifies before/after merge; no
auto-merge.

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- **Engine substitution**: make `_rule_matches_runtime_scope` delegate
  to the pure contract (touches live runtime — guarded by R1's parity
  matrix as the regression net).
- **Operator/key extension** (RFC Option C).
- **Fail-open → fail-closed hardening** for corrupt stored predicates.
- **`_ALLOWED_TYPES` action-set widening** (orthogonal).

## 9. Reviewer Focus

- Does the pure contract mirror `_normalize_match_predicates` +
  `_normalize_runtime_context` + steps 1 & 3–8 of
  `_rule_matches_runtime_scope` **exactly** (truthy-only equality;
  actor-role intersection; absent = wildcard; empty = `True`)?
- Is **fail-open** pinned — illegal `match_predicates` → empty
  predicate **but `workflow_map_id` preserved** — with a comment citing
  line 2169, and required in the compat matrix?
- Is `workflow_map_id` modeled as an **independent** constructor input
  (not a `match_predicate`) and matched independently?
- Is the parity matrix a real cross-check vs the live service with
  `workflow_map_id` varied, not a tautology?
- Is the module pure (no service/DB/router import; the parity test
  imports the service, the module does not)?
- Did anything edit the engine/router, add operators/keys, change
  fail-open, add schema, or touch the prior contracts? It must not.
