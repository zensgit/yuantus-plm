# Claude Taskbook: Odoo18 Automation-Rule Predicate Pure-Contract R1

Date: 2026-05-15

Type: **Doc-only taskbook.** Changes no runtime, no schema, no rule
engine. Specifies the contract a later, separately opted-in
implementation PR will deliver. Merging this taskbook does NOT authorize
that code.

## 1. Purpose

Implements the **Option B** decision from the automation-rule RFC
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_AUTOMATION_RULE_DSL_RFC_20260515.md`,
merged `534238f`): the rule-matching `match_predicates` facility already
exists but is **embedded** in the DB-bound `WorkflowCustomActionService`
with no isolated, testable, refactor-safe surface. R1 extracts its
**exact current semantics** into a small **pure** contract plus a
**service-parity compat matrix** — *behavior-preserving*, no engine
edit, no schema, no `eval`/parser.

R1 follows the proven contract-first pattern of the five shipped
contracts (workorder version-lock, consumption MES, pack-and-go,
maintenance, ECR intake): pure DTO + pure evaluator + drift/parity
tests, default no-op.

## 2. Current Reality (grounded — read before implementing)

`src/yuantus/meta_engine/services/parallel_tasks_service.py`,
`WorkflowCustomActionService`:

- `_ALLOWED_MATCH_PREDICATES` (line 2009) = `{stage_id, eco_priority,
  actor_roles, product_id, eco_type}`.
- `_normalize_match_predicates` (line 2112): validates/normalizes —
  `stage_id`/`product_id` → optional trimmed string; `eco_priority` →
  lowercased, must be `{low,normal,high,urgent}`; `eco_type` →
  lowercased, must be `{bom,product,document}`; `actor_roles` →
  de-duplicated lowercased string list; unknown keys → `ValueError`;
  empties dropped (so `{}` means "no constraint").
- `_rule_match_predicates` (line 2169): reads
  `rule.action_params["match_predicates"]`, calls
  `_normalize_match_predicates`, and **on `ValueError` returns `{}`**
  → **fail-open** (an illegal stored predicate degrades to "match
  everything").
- `_normalize_runtime_context` (line 2177): normalizes the runtime
  facts the same way (lowercase `eco_priority`/`eco_type`, optional
  strings, lowercased `actor_roles` list).
- `_rule_matches_runtime_scope` (line 2195) decides if a rule applies.
  Its body, in order:
  1. **`rule.workflow_map_id`** (a *rule column*, NOT a
     match-predicate): if set and `!= context["workflow_map_id"]` →
     `False`.
  2. effective predicate = `_rule_match_predicates(rule)` (fail-open).
  3. `stage_id`: if predicate value truthy and `!=
     context["stage_id"]` → `False`.
  4. `eco_priority`: same pattern.
  5. `product_id`: same pattern.
  6. `eco_type`: same pattern.
  7. `actor_roles`: if predicate list non-empty and
     `set(context.actor_roles) ∩ predicate.actor_roles == ∅` → `False`.
  8. else `True`.
  Each scalar check is **"only enforced if the predicate value is
  truthy"** — an absent predicate key is a wildcard.
- Wired into ECO transitions via `eco_service.py:243`
  (`WorkflowCustomActionService(...).evaluate_transition(...)`).
- Existing tests:
  `test_workflow_custom_actions_match_runtime_scope_predicates`
  (`test_parallel_tasks_services.py` ~line 1400) and
  `test_workflow_custom_actions_match_context_predicates` (~line 1525).

## 3. Scope Boundary (read carefully)

The pure contract reproduces **only the predicate portion** — steps
2–8 above (the 5 `_ALLOWED_MATCH_PREDICATES` keys + the fail-open
derivation + the relevant context normalization).

**`workflow_map_id` (step 1) is explicitly OUT of contract scope.** It
is a rule-level column scope filter, not a `match_predicate`. The
`WorkflowCustomActionService` keeps owning it. To make the compat
matrix a sound apples-to-apples comparison, the parity harness
constructs service rules with `workflow_map_id = None` (so step 1 is a
no-op) and compares the service's `_rule_matches_runtime_scope` outcome
against the pure `evaluate_rule_predicate`. This boundary must be
stated in the impl PR's DEV/verification MD (same kind of explicit
boundary as the maintenance-bridge "absent workcenter" decision).

## 4. R1 Target Output (for the later, separately opted-in impl PR)

New pure module, e.g.
`src/yuantus/meta_engine/services/automation_rule_predicate_contract.py`:

- `RulePredicate` — frozen Pydantic v2, `extra="forbid"`: optional
  `stage_id`, `eco_priority`, `product_id`, `eco_type`, and
  `actor_roles: tuple[str, ...]`. Validation **mirrors**
  `_normalize_match_predicates` exactly (enum domains for
  `eco_priority`/`eco_type`, lowercasing, de-dup, empties→absent).
- `RuleFacts` — frozen Pydantic v2: the runtime context counterpart
  (`stage_id`, `eco_priority`, `product_id`, `eco_type`,
  `actor_roles`), normalized exactly like `_normalize_runtime_context`.
- `resolve_effective_predicate(raw: dict | None) -> RulePredicate` —
  pure mirror of `_rule_match_predicates`: normalize; **on validation
  error return the empty (wildcard) predicate** — pinning the
  **fail-open** behavior bit-for-bit. (Pure: it raises nothing; an
  illegal raw predicate yields the match-all predicate.)
- `evaluate_rule_predicate(predicate: RulePredicate, facts: RuleFacts)
  -> bool` — pure mirror of steps 3–8: truthy-only equality for
  `stage_id`/`eco_priority`/`product_id`/`eco_type`, set-intersection
  for `actor_roles`; absent key = wildcard; empty predicate → `True`.

No DB, no `eval`, no parser, no engine wiring, no behavior change. The
service keeps its own code in R1 (the contract is **parallel**, not yet
substituted — substitution is a separate opt-in).

## 5. Tests Required (in the later impl PR)

New `test_automation_rule_predicate_contract.py`:

- Predicate validation: unknown `eco_priority`/`eco_type` rejected;
  lowercasing; `actor_roles` de-dup/lowercase; `extra=forbid`; frozen.
- Evaluator: empty predicate → always `True`; each single-key predicate
  matches/!matches per truthy-equality; `actor_roles` intersection
  (match iff overlap); multi-key AND semantics; absent key is wildcard.
- **Fail-open pin**: `resolve_effective_predicate` of an illegal raw
  predicate (e.g. unknown key, bad `eco_priority`) returns the empty
  predicate, and `evaluate_rule_predicate` then returns `True`
  (match-all) — asserted explicitly with a comment citing
  `_rule_match_predicates` line 2169 as the pinned behavior.
- **Service-parity compat matrix** (the core R1 value): a table of
  `(raw_match_predicates, runtime_context)` cases — including legal,
  empty, wildcard, multi-key, actor-role, and **illegal/fail-open** —
  each asserted to produce the **same boolean** from (a)
  `WorkflowCustomActionService._rule_matches_runtime_scope` on a rule
  built with `workflow_map_id=None`, and (b) the pure
  `evaluate_rule_predicate(resolve_effective_predicate(raw),
  RuleFacts(**ctx))`. This is a real cross-check against the live
  service, not a tautology.
- Purity guard: AST import scan asserts the module imports nothing from
  `yuantus.database` / `sqlalchemy` / a router / `plugins`; it MAY
  import nothing from the service either — the parity *test* imports
  the service, the *module* does not. (If enum domains are needed,
  import them from the model layer, not the service.)
- Drift guard: the contract's accepted predicate-key set equals
  `WorkflowCustomActionService._ALLOWED_MATCH_PREDICATES`, and the
  `eco_priority`/`eco_type` domains equal the service's
  `_ALLOWED_ECO_PRIORITIES`/`_ALLOWED_ECO_TYPES` — introspected, so a
  change on either side fails loudly.

Doc-index trio stays green for the impl PR's DEV/verification MD.

## 6. Verification Commands (for the impl PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_automation_rule_predicate_contract.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py
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

- **No engine edit.** `WorkflowCustomActionService` /
  `_rule_matches_runtime_scope` / `_rule_match_predicates` are **not**
  modified; the contract is parallel only. Substituting the service to
  delegate to the contract is a **separate** opt-in.
- **No `workflow_map_id` in the contract** — out of scope per §3.
- **No operator/key extension** (`ne`/`in`/`not_in`/new keys) — RFC
  Option C, separate opt-in.
- **No fail-open → fail-closed hardening** — separate opt-in; R1
  *pins* fail-open, it does not change it.
- **No `_ALLOWED_TYPES` action-set widening** — orthogonal, undecided.
- No route / table / migration / schema / DB read / feature flag /
  `eval` / parser.
- No contact with the workorder version-lock, consumption MES,
  pack-and-go, maintenance bridge, or ECR intake contracts.
- `.claude/` and `local-dev-env/` stay out of git.

## 8. Decision Gate / Handoff

Doc-only. The implementation PR (pure module + tests +
DEV/verification MD) is owned by Claude Code **only after this taskbook
is merged AND a separate explicit opt-in is given**, on branch:

`feat/odoo18-automation-rule-predicate-contract-r1-20260515`

Follow-ups, each its own separate opt-in (explicitly NOT in R1):

- **Engine substitution**: make `_rule_matches_runtime_scope` delegate
  its predicate portion to the pure contract (touches live runtime —
  guarded by R1's parity matrix as the regression net).
- **Operator/key extension** (RFC Option C).
- **Fail-open → fail-closed hardening** for corrupt stored predicates.
- **`_ALLOWED_TYPES` action-set widening** (orthogonal).

## 9. Reviewer Focus

- Does the pure contract mirror `_normalize_match_predicates` +
  steps 3–8 of `_rule_matches_runtime_scope` **exactly** (truthy-only
  equality; actor-role intersection; absent = wildcard; empty = True)?
- Is the **fail-open** behavior pinned (illegal raw → empty predicate →
  match-all) with a comment citing line 2169, and is the compat matrix
  required to cover it?
- Is the parity matrix a real cross-check vs the live service (rules
  built with `workflow_map_id=None`), not a tautology?
- Is `workflow_map_id` correctly **excluded** from the contract and the
  boundary documented?
- Is the module pure (no service/DB/router import; parity test imports
  the service, the module does not)?
- Did anything edit the engine, add operators/keys, change fail-open,
  add schema/route, or touch the prior contracts? It must not.
