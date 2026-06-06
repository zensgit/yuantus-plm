# DEV & Verification: OdooPLM 19 CAD-PDM B2 Assembly Release Hard Gate

Date: 2026-06-05

Implements **B2** from the CAD-PDM borrow program: a released parent must not
reference **unreleased direct `ASSEMBLY` children** (the WP1.2 product structure).
Builds directly on the WP1.2 `ASSEMBLY` Part↔Part relationship model (#726/#728/#729)
and the `release_validation` ruleset machinery (`baseline_release`/`eco_apply`
precedent). No new route, no traversal change, no status-semantics change.

## Scope (this PR)

- New `item_release` ruleset kind in `services/release_validation.py`
  (`item.exists` → `item.not_already_released` → `bom.children_all_released`),
  with a `readiness` variant that drops `item.not_already_released` (the item is
  mid-transition to Released when the promote gate evaluates it).
- New `services/item_release_service.py` (`ItemReleaseService`):
  - `assert_children_released(item_id)` — the **hard gate**: error strings for
    unreleased direct `ASSEMBLY` children (empty ⇒ pass). Focused — checks only
    children, never re-fetches / existence-checks the promoting item.
  - `get_release_diagnostics(item_id, ruleset_id=)` — advisory surface mirroring
    `baseline_service.get_release_diagnostics` (errors/warnings of `ValidationIssue`).
- Hard block in `lifecycle/service.py::promote` as an **early precondition**
  (immediately after the permission check, *before* the before-transition hooks,
  the state mutation, the `on_enter_state` hooks, and the workflow start), gated on
  `target_state_obj.name == "Released"`.

## As built (against the locked model)

- **Early precondition, no rollback** — the gate runs before any state mutation or
  side effect, so a *blocked* release never emits "entered Released" hooks, never
  mutates `item.state`/`item.current_state`, and never creates a workflow instance;
  it simply returns `PromoteResult(success=False, ...)`. (The registered
  `on_enter_state` hooks and `start_workflow` are in-session/`flush`-only today, so
  a late gate would have been merely wasteful, not unsafe — but a precondition
  belongs before the action it guards.)
- **Trigger convention** — keyed on `target_state_obj.name == "Released"`, the
  **codebase-wide** release marker: the same condition gates the version-release
  block, the release hook (`lifecycle/hooks.py`), and the workflow service
  (`workflow/service.py`). The seeded released state (`seeder/meta/lifecycles.py`)
  is named `"Released"` **and** carries `is_released=True`. **Assumption (explicit):**
  a map whose released state is *not* named `"Released"` is invisible to all four of
  these paths, not just B2; aligning the whole release machinery to `is_released`
  is a separate, deliberately-deferred change. B2 matches the existing convention
  rather than silently diverging from it.
- **Authoritative child check, fail-closed fallback** — `_is_released(child)`
  reads the child's `LifecycleState.is_released` flag (not a name match). The
  string fallback (used only when no `LifecycleState` row resolves) is **just
  `"released"`** — deliberately narrow: `"approved"` is an approval/ECO concept,
  not a Part release state (the seeded Part lifecycle has no `Approved`), so
  counting it would let an unreleased child pass (fail-open). The *trigger* is
  name-based (lockstep with version release); the *child verdict* is flag-based and
  the fallback fails **closed**.
- **Edge model, fail-closed on dangling edges** — `_direct_assembly_children`
  queries the `ASSEMBLY` edge Items directly (`source_id == parent`,
  `item_type_id == "ASSEMBLY"`, `is_current`), then resolves each `related_id`. A
  **dangling edge** (`related_id` NULL or pointing at a missing/removed Item →
  `session.get` returns `None`) is a hard **block**, not a silent skip: diagnostics
  emit `child_missing` (+ `relationship_id`) and `promote` refuses — a broken BOM
  reference must not release. A DB with no `ASSEMBLY` type/edges yields no rows →
  **vacuous pass** (leaf parts release freely).
- **Direct children only** — the gate is one level (a child assembly is itself
  gated when *it* releases), so releasing bottom-up is sufficient and the gate is
  O(direct children), not a full-tree traversal. Deep-tree readiness stays the
  advisory `stale-drawings`/readiness surface, not this hard block.
- **Existence safety** — `get_release_ruleset` always forces `item.exists` first;
  `get_release_diagnostics` short-circuits on a missing item. The hard gate path
  (`assert_children_released`) deliberately skips item existence — the promoting
  item is in hand.
- **No route** — service + lifecycle-internal gate only; **route-count stays 705**
  (no pin bump). New test registered in `ci.yml` contracts list (sorted, between
  `test_integration_capabilities` and `test_job_queue_tx_boundary_contracts`) +
  `conftest.py` no-DB allowlist.

## Not in this PR (non-goals)

- No `Superseded`/state-semantics work (that is B1 — taskbook-first, deferred).
- No aggregation of `item_release` diagnostics into `release_readiness` (advisory
  follow-up; the evaluator is ready for it).
- No version-switch auto-recompute, no pack-and-go, no write endpoints.

## Verification (Python 3.11 venv, requirements.lock)

- `pytest test_item_release_gate.py` → **12 passed**: evaluator (unreleased-child
  error, released-child ok, no-children vacuous pass, default flags
  already-released, readiness skips not-already-released, missing item, **dangling
  edge → `child_missing`**, **`state="Approved"` w/o state row → blocked**) + the
  real `LifecycleService.promote` hard gate (blocks on unreleased child **and on a
  dangling edge**, with **Draft left intact** — state never mutated; succeeds when
  child released; leaf succeeds).
- **Hermetic / order-independent** — an autouse fixture clears the lru-cached
  `get_settings()`; verified the test passes even when `test_release_validation_
  directory.py` (which sets a deliberately-bad `RELEASE_VALIDATION_RULESETS_JSON`
  and, on a local 401, skips its own cache cleanup) runs **first**.
- **Blast radius** — the only allowlisted no-DB test that promotes to `Released`
  is this one; no other contract test exercises the gate. `release_validation`
  directory/wiring tests use specific-kind membership asserts (not an exact kind
  set), so the new `item_release` kind does not break them.
- `create_app()` unchanged at **705 routes**; all 4 route-count contracts pass.
- `test_lifecycle_version_integration.py` (a fully-mocked, **not-in-CI**,
  pre-existing-red promote test) updated so its mocked `query(Item)` returns `[]`
  for the gate's children query — keeps the gate transparent there rather than
  raising on a `MagicMock`.
- `git diff --check` clean.
