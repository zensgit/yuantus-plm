# Odoo18 Automation-Rule Predicate Pure-Contract R1 — Development and Verification

Date: 2026-05-15

## 1. Goal

Implement R1 of the automation-rule predicate taskbook
(`docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_AUTOMATION_RULE_PREDICATE_CONTRACT_20260515.md`,
merged `03517a1`) — RFC #575 **Option B**. Extract the **already
embedded** `match_predicates` matching semantics out of the DB-bound
`WorkflowCustomActionService` into a **parallel pure contract** plus a
**service-parity matrix** that pins the current behavior bit-for-bit.

R1 is **pure, parallel, behavior-preserving**: a module + tests + this
MD. No service/router/schema/runtime change. The service keeps its own
code; substituting it to delegate here is a separate, later opt-in.

## 2. Scope

### Added

- `src/yuantus/meta_engine/services/automation_rule_predicate_contract.py`
- `src/yuantus/meta_engine/tests/test_automation_rule_predicate_contract.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_AUTOMATION_RULE_PREDICATE_CONTRACT_R1_20260515.md`

### Modified

- `docs/DELIVERY_DOC_INDEX.md` (one index line)

`WorkflowCustomActionService`, `_rule_matches_runtime_scope`,
`_rule_match_predicates`, the parallel-tasks router, ORM models, and the
prior five Odoo18 contracts are **unchanged**.

## 3. Contract

### 3.1 `WorkflowRulePredicate` (Pydantic v2, frozen, `extra="forbid"`)

All fields optional, absent = wildcard: `workflow_map_id`, `stage_id`,
`eco_priority`, `actor_roles` (tuple), `product_id`, `eco_type`.
`eco_priority`/`eco_type` validators reject values outside the live
`ECOPriority`/`ECOType` domains. `workflow_map_id` is an **independent**
field (a rule-column scope filter, NOT part of `match_predicates`).
`is_empty()` is true iff no constraint at all.

### 3.2 `WorkflowRuleFacts` (Pydantic v2, frozen, `extra="forbid"`)

Runtime-context counterpart. `from_context(dict)` normalizes exactly
like `WorkflowCustomActionService._normalize_runtime_context`
(`_normalize_optional_string`; lowercase `eco_priority`/`eco_type`;
`actor_roles` → de-duplicated lowercased tuple).

### 3.3 `normalize_workflow_rule_predicate(workflow_map_id, match_predicates)`

Pure mirror of `rule.workflow_map_id` + `_rule_match_predicates`:

- `workflow_map_id` normalized independently
  (`_normalize_optional_string`).
- `match_predicates` strict-normalized by a pure mirror of
  `_normalize_match_predicates` (unsupported key / bad enum / non-array
  `actor_roles` / non-dict → `ValueError`; empties dropped).
- **Fail-open (pinned, not hardened):** on *any* `match_predicates`
  validation error the result degrades to the empty predicate **but the
  normalized `workflow_map_id` is preserved** — bit-for-bit with the
  service, where `workflow_map_id` is a rule column read at
  `_rule_matches_runtime_scope` step 1, *before* and independent of the
  predicate fail-open path (`_rule_match_predicates` line 2169). The
  function raises nothing.

### 3.4 `evaluate_rule_predicate(predicate, facts) -> bool`

Pure mirror of `_rule_matches_runtime_scope` step order and
"only-enforced-if-truthy" semantics: `workflow_map_id` (step 1), then
`stage_id` / `eco_priority` / `product_id` / `eco_type` truthy-exact
equality, then `actor_roles` lowercase set-intersection. Absent =
wildcard; empty predicate → `True`.

## 4. Test Matrix

`src/yuantus/meta_engine/tests/test_automation_rule_predicate_contract.py`
(test groups; counts are a point-in-time snapshot and grow as cases are
added):

- **DTO**: frozen, `extra=forbid`, unknown-enum rejected,
  `actor_roles` de-dup/lowercase, blank→absent, facts normalization.
- **Evaluator matrix**: empty → match-all; single-key truthy-equality
  (absent fact for a constrained key → no match); `actor_roles`
  intersection; multi-key AND.
- **`workflow_map_id` independence**: matches independently of
  `match_predicates`; ANDed with predicates when both set.
- **Fail-open pin**: 5 illegal stored `match_predicates`
  (unsupported key, bad `eco_priority`, bad `eco_type`, non-array
  `actor_roles`, non-dict) → empty predicate **but `workflow_map_id`
  preserved**; comment cites `_rule_match_predicates` line 2169 and
  states R1 must NOT harden it.
- **Service-parity matrix** (core R1 value): 19 cases of
  `(workflow_map_id, raw_match_predicates, runtime_context)` — legal,
  empty, wildcard, multi-key, actor-role, `workflow_map_id` set/unset,
  and illegal/fail-open — each asserted to produce the **same boolean**
  from the real `WorkflowCustomActionService._rule_matches_runtime_scope`
  (with `_normalize_runtime_context`) and from
  `evaluate_rule_predicate(normalize_workflow_rule_predicate(...),
  WorkflowRuleFacts.from_context(...))`. A real cross-check, not a
  tautology. (`WorkflowCustomActionRule` is instantiated in-memory; the
  service is built with a `MagicMock` session — `_rule_matches_runtime_scope`
  does not touch the session.)
- **Purity guard**: AST import scan asserts the module imports nothing
  from `yuantus.database` / `sqlalchemy` / `parallel_tasks_service` /
  `WorkflowCustomActionService` / a router / `plugins`, and *does*
  import `yuantus.meta_engine.models.eco` (enum source). The parity
  test imports the service; the module does not.
- **Drift guard**: contract `_ALLOWED_MATCH_PREDICATE_KEYS` ==
  `WorkflowCustomActionService._ALLOWED_MATCH_PREDICATES`; contract
  `_ALLOWED_ECO_PRIORITIES`/`_ALLOWED_ECO_TYPES` == the service's
  constants — introspected, so a change on either side fails loudly.

## 5. Verification Commands

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

Observed as of 2026-05-15: contract tests all passed; parallel-tasks
regression (`test_parallel_tasks_services.py` +
`test_parallel_tasks_router.py`) all passed, no regression; doc-index
trio passed; py_compile clean; `git diff --check` clean.

## 6. Non-Goals (reaffirmed from taskbook §7)

No service edit / no router edit (contract is parallel only); no
operator/key extension (RFC Option C); no fail-open→fail-closed
hardening (R1 *pins* fail-open); no `_ALLOWED_TYPES` action-set
widening; no route / table / migration / schema / DB read / feature
flag / `eval` / parser / runtime wiring. No contact with the prior five
Odoo18 contracts. `.claude/` and `local-dev-env/` stay out of git.

## 7. Follow-ups (each its own separate opt-in)

- **Engine substitution**: make `_rule_matches_runtime_scope` delegate
  its decision to this contract — guarded by R1's parity matrix as the
  regression net.
- **Operator/key extension** (RFC Option C).
- **Fail-open → fail-closed hardening** for corrupt stored predicates.
- **`_ALLOWED_TYPES` action-set widening** (orthogonal).
