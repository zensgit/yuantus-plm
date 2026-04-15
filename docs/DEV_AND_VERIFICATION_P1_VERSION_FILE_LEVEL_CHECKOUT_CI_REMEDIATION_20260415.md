# P1 Version File-Level Checkout CI Remediation

Date: 2026-04-15

## Trigger

PR [#202](https://github.com/zensgit/yuantus-plm/pull/202) came up with:

- `contracts`: pass
- `regression`: pass
- `plugin-tests`: fail

GitHub reported `mergeStateStatus=UNSTABLE`.

## Root Cause

The failing step was the CI migration smoke in `plugin-tests`:

```text
python -m alembic -c alembic.ini upgrade head
```

The new migration
`migrations/versions/d2e3f4a5b6c7_add_version_file_checkout_fields.py`
used `op.create_foreign_key(...)` after adding columns.

That works on databases that support `ALTER TABLE ... ADD CONSTRAINT`, but the
CI job runs against SQLite, where Alembic raised:

```text
NotImplementedError: No support for ALTER of constraints in SQLite dialect.
Please refer to the batch mode feature...
```

## Remediation

The migration was changed to branch on dialect:

- SQLite:
  - use `op.batch_alter_table(..., recreate="always")`
  - add the two columns and foreign key inside batch mode
- non-SQLite:
  - keep the direct `add_column()` + `create_foreign_key()` path

The downgrade path was updated the same way.

## Local Verification

Focused local regression was re-run after the migration fix:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Observed:

- `29 passed, 1 warning`

Note:

- the local shell did not have an `alembic` module installed, so the exact CI
  `upgrade head` command could not be replayed locally
- the fix was instead validated by targeted regression plus GitHub check rerun

## Outcome

The feature slice itself did not change semantically.

This remediation only made the migration SQLite-safe so the PR can pass the CI
job that runs `upgrade head` before plugin tests.

## Claude Code CLI

`Claude Code CLI` remained available in this slice, but it was not used as the
primary execution path for the fix. The remediation was implemented and
validated locally, then intended to be confirmed by GitHub check rerun.
