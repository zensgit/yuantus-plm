# Odoo18 Maintenance Runtime Wiring R1 - Development and Verification

Date: 2026-05-18

## 1. Goal

Wire the previously merged maintenance DB-resolver and maintenance workorder
bridge contracts into one narrow runtime consumer.

This slice deliberately does **not** create a new plugin directory. In the
current codebase, the meaningful runtime seam is routing release validation:
manufacturing already owns `RoutingService`, and release rulesets already decide
which operational checks block a routing release. The new maintenance gate is
therefore opt-in via release-validation, not default-on behavior.

## 2. Scope

Added:

- `src/yuantus/meta_engine/tests/test_maintenance_routing_release_wiring.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_MAINTENANCE_RUNTIME_WIRING_R1_20260518.md`

Modified:

- `src/yuantus/meta_engine/manufacturing/routing_service.py`
- `src/yuantus/meta_engine/services/release_validation.py`
- `docs/DELIVERY_DOC_INDEX.md`

Unchanged by design:

- `src/yuantus/meta_engine/services/maintenance_workorder_bridge_contract.py`
- `src/yuantus/meta_engine/services/maintenance_db_resolver_contract.py`
- maintenance ORM models
- manufacturing ORM models
- routers and UI
- migrations, tenant baselines, seeds, feature flags

## 3. Runtime Contract

`release_validation.py` now defines one additional allowed routing rule:

```text
routing.operation_workcenters_maintenance_ready
```

The rule is included in a new built-in routing ruleset:

```text
routing_release:maintenance_ready
```

The default and existing readiness rulesets are unchanged. This preserves the
current release path unless an operator or configured caller explicitly chooses
the maintenance-aware ruleset.

`RoutingService` now has two narrow methods:

- `resolve_workcenter_maintenance_descriptors(workcenter_id)`
- `assert_workcenter_maintenance_ready(workcenter_id)`

The service performs the DB read because it already owns manufacturing runtime
release checks. It fetches:

- `Equipment` rows for the target `workcenter_id`, ordered by equipment id;
- `MaintenanceRequest` rows for each equipment, ordered by `created_at DESC`,
  then id descending for deterministic tie-breaks.

It then reuses the merged contracts:

- `EquipmentRow` / `MaintenanceRequestRow`
- `resolve_workcenter_maintenance_descriptors(...)`
- `assert_workcenter_ready(...)`

No readiness arithmetic is reimplemented in the routing service.

## 4. Release Behavior

When `routing.operation_workcenters_maintenance_ready` is active:

- each operation workcenter is first resolved through the existing
  `_resolve_workcenter(...)` path, preserving current workcenter existence,
  activity, id/code, plant, and line checks;
- the resolved workcenter id is checked by `assert_workcenter_maintenance_ready`;
- `workcenter_blocked:` is reported in diagnostics as
  `workcenter_maintenance_blocked`;
- `workcenter_unknown:` is reported as `workcenter_maintenance_unknown`;
- `workcenter_invalid:` is reported as `workcenter_maintenance_invalid`;
- `release_routing(...)` raises the underlying `ValueError` and does not release.

When the rule is absent, there is no maintenance DB read and existing routing
release behavior is preserved.

## 5. Test Matrix

New focused tests cover:

- runtime DB row fetch into the maintenance DB-resolver and bridge assertion;
- `submitted` maintenance request blocks the workcenter;
- `draft` request is surfaced in descriptors but does not block readiness;
- default routing release ruleset does not include the maintenance gate;
- built-in `maintenance_ready` ruleset and allowed-rule directory expose the new
  rule;
- release diagnostics maps maintenance blockage to a distinct issue code;
- `release_routing(...)` raises when the maintenance-ready rule fails.

Existing contract tests still cover the pure bridge and DB resolver semantics.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_maintenance_routing_release_wiring.py \
  src/yuantus/meta_engine/tests/test_maintenance_db_resolver_contract.py \
  src/yuantus/meta_engine/tests/test_maintenance_workorder_bridge_contract.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_manufacturing_release_diagnostics.py \
  src/yuantus/meta_engine/tests/test_manufacturing_routing_workcenter_validation.py
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
  src/yuantus/meta_engine/manufacturing/routing_service.py \
  src/yuantus/meta_engine/services/release_validation.py \
  src/yuantus/meta_engine/tests/test_maintenance_routing_release_wiring.py
git diff --check
```

Observed on 2026-05-18:

- maintenance runtime/DB-resolver/bridge tests: `54 passed`
- release diagnostics/workcenter validation tests: `14 passed`
- doc-index/R2 portfolio tests: `14 passed`
- `py_compile`: clean
- `git diff --check`: clean

Note: `test_release_validation_directory.py` was not used as a gate for this
slice because the current route-level test returns `401 Missing bearer token`
under its simple dependency override. The new wiring test verifies
`get_release_validation_directory()` directly for the new allowed rule and
`maintenance_ready` built-in ruleset, which is the service behavior changed by
this PR.

## 7. Non-Goals

- No default-on release behavior change.
- No route or UI field.
- No schema, migration, tenant baseline, seed, or feature flag.
- No edit to the pure maintenance bridge or DB-resolver contracts.
- No FK hardening for `Equipment.workcenter_id`.
- No operation-start workflow. This slice only adds a release-validation
  consumer; a future real workorder execution gate remains a separate opt-in.
- No `.claude/` or `local-dev-env/` tracking.

## 8. Follow-Ups

- Route/API exposure can stay as-is because callers can already pass
  `ruleset_id=maintenance_ready` to release diagnostics and release endpoints.
- A future workorder execution/start endpoint can call the same
  `assert_workcenter_maintenance_ready(...)` seam.
- FK hardening of `Equipment.workcenter_id` remains separate.
