# DEV & Verification — Phase 3 Tenant Table Classification Stop Gate

Date: 2026-04-27

## 1. Goal

Create the written table-classification artifact required before P3.4 data
migration / runtime cutover can begin.

This is a stop-gate PR. It does not start P3.4 execution.

## 2. Delivered Artifacts

- `docs/TENANT_TABLE_CLASSIFICATION_20260427.md`
- `src/yuantus/tests/test_tenant_table_classification_contracts.py`
- `docs/DELIVERY_DOC_INDEX.md` index entries

## 3. Design Decisions

The classification is code-derived, not manually guessed:

- Global/control-plane table list comes from `GLOBAL_TABLE_NAMES`.
- Tenant application table list comes from `build_tenant_metadata().tables`.
- The existing exhaustive partition invariant remains the source of truth:
  `combined == GLOBAL_TABLE_NAMES | tenant_set`, with a disjoint partition.

The artifact explicitly keeps P3.4 blocked. Only P3.3.1 + P3.3.2 + P3.3.3 are
marked complete; the pilot tenant, non-production DSN, backup owner, rehearsal
window, and sign-off remain unchecked.

## 4. Contract Coverage

`test_tenant_table_classification_contracts.py` pins four things:

1. The artifact exists and states that sign-off is still pending.
2. The global table section exactly matches `GLOBAL_TABLE_NAMES`.
3. The tenant table section exactly matches `build_tenant_metadata().tables`.
4. The stop gate keeps runtime cutover disabled and requires the remaining
   operator inputs.

This makes table classification a reviewable artifact without letting it drift
from the actual metadata that drives tenant Alembic.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_table_classification_contracts.py \
  src/yuantus/tests/test_tenant_alembic_env.py \
  src/yuantus/tests/test_tenant_baseline_revision.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python scripts/generate_tenant_baseline.py --check
PYTHONPATH=src .venv/bin/python -c "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"
git diff --check
```

Result:

```text
34 passed, 1 skipped, 1 warning in 1.76s
generator --check: ok: committed revision matches generator output
boot: routes=672 middleware=4
git diff --check: clean
```

## 6. Scope Controls

No runtime files are changed.

No migration revision is changed.

No data migration tool is introduced.

No production setting is changed.

## 7. Next Step

After this artifact is reviewed, the next bounded development slice should be
P3.4.1 migration dry-run tooling:

- read-only export planning;
- FK-safe table order;
- source row-count snapshot;
- global table exclusion checks;
- no writes to a target database.

P3.4.2 import rehearsal should wait for a non-production PostgreSQL DSN and an
approved pilot tenant.
