# P1 CAD PR Unstable CI Remediation

Date: 2026-04-15
Branch: `baseline/mainline-20260414-150835`
PR: `#201`

## Summary

PR `#201` was `mergeable=true` but `mergeStateStatus=UNSTABLE`.

The unstable state mapped to three concrete failure buckets:

1. `plugin-tests` / `regression`
   - Root cause: main Alembic tree had two heads (`a2b2c3d4e7a6`, `f7a8b9c0d1e2`), while CI/runtime still executed `alembic.ini upgrade head`.
2. `contracts`
   - Root causes:
     - `docs/DELIVERY_DOC_INDEX.md` `## Development & Verification` section was no longer path-sorted.
     - `README.md` `## Runbooks` omitted three committed runbooks.
     - declared ORM table `meta_eco_routing_changes` had no `create_table` migration coverage.
     - historical removed table `cad_conversion_jobs` was still a legitimate migration-only table but had no allowlist entry.
3. `plugin-tests` hidden follow-up after the migration smoke issue
   - `plugins/yuantus-bom-compare/main.py` hit a Pydantic forward-ref rebuild issue under the importlib-based plugin test harness.

## Design Decision

For the Alembic failure, I chose:

- add a merge migration that reunifies the main meta DB back to a single head
- keep operational commands on `upgrade head`

I explicitly did **not** switch runtime/CI commands to `upgrade heads`.

Reason:

- `upgrade head` remains a useful guardrail against accidentally introducing a new unresolved Alembic branch.
- this fixes the current structural problem instead of masking it.

`Claude Code CLI` was used as a short read-only sidecar to sanity-check this decision; the implementation and validation below were done locally.

## Code Changes

### 1. Merge migration + ECO routing table coverage

Added:

- `migrations/versions/c1d2e3f4a5b6_merge_heads_add_eco_routing_changes.py`

What it does:

- merges heads `a2b2c3d4e7a6` and `f7a8b9c0d1e2`
- creates `meta_eco_routing_changes` if missing
- creates indexes for `eco_id` and `change_type`

Result:

- `alembic.ini` now has a single head again
- `upgrade head` is valid in CI/runtime

### 2. Migration coverage contract fix

Updated:

- `src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py`

What changed:

- added `_MIGRATION_ONLY_TABLE_ALLOWLIST = ("cad_conversion_jobs",)`
- excluded allowlisted historical migration-only tables from the `extra migrated tables` assertion
- added a sorted/stale contract for that allowlist

### 3. Docs contracts fix

Updated:

- `README.md`
- `docs/DELIVERY_DOC_INDEX.md`

What changed:

- added missing runbook references:
  - `docs/RUNBOOK_CAD_LEGACY_CONVERSION_QUEUE_AUDIT.md`
  - `docs/RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md`
  - `docs/RUNBOOK_P1_CAD_COMMIT_SEQUENCE_20260414.md`
- restored path-sorted order in `docs/DELIVERY_DOC_INDEX.md > ## Development & Verification`

### 4. Plugin import/rebuild fix

Updated:

- `plugins/yuantus-bom-compare/main.py`

What changed:

- added `BomCompareRequest.model_rebuild()` after `BomCompareFilters` definition

Reason:

- the plugin test imports the module via `importlib.util.spec_from_file_location(...)`
- under that path, FastAPI/Pydantic adapter construction could happen before the forward reference resolved cleanly

## Validation

### Contracts

Command:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py
```

Result:

- `8 passed`

### Plugin tests

Command:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py
```

Result:

- `31 passed, 1 skipped, 1 warning`

### ECO routing regression

Command:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_routing_change.py
```

Result:

- `18 passed, 1 warning`

### Alembic smoke

Commands:

```bash
YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_pr201_ci_fix.db \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m alembic -c alembic.ini heads

YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_pr201_ci_fix.db \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m alembic -c alembic.ini upgrade head
```

Results:

- heads: `c1d2e3f4a5b6 (head)`
- `upgrade head` completed successfully on a fresh SQLite DB

### Syntax

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc python3 -m py_compile \
  plugins/yuantus-bom-compare/main.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
  migrations/versions/c1d2e3f4a5b6_merge_heads_add_eco_routing_changes.py
```

Result:

- passed

## Notes

- This remediation focused on the concrete blockers behind PR `#201` being `UNSTABLE`.
- I did **not** run a full-repository regression in this slice.
- Existing environment warnings were limited to the previously known `urllib3/LibreSSL` warning.
