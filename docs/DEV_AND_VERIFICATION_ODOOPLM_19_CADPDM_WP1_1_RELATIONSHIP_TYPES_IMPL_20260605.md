# DEV & Verification: OdooPLM 19 CAD-PDM WP1.1 Relationship Types Implementation

Date: 2026-06-05

Records the implementation of WP1.1 from
`ODOOPLM_BORROW_DEVELOPMENT_PLAN_AND_TODO_20260604.md`, under the WP1.0
representation decision taskbook
`DEVELOPMENT_WP1_0_CAD_PDM_REPRESENTATION_DECISION_TASKBOOK_20260604.md`.

## Scope

- Seed exactly two CAD-PDM relationship `ItemType` rows:
  - `ASSEMBLY`
  - `REFERENCE`
- Both are strict Part-to-Part relationship ItemTypes:
  - `is_relationship = true`
  - `is_versionable = false`
  - `source_item_type_id = "Part"`
  - `related_item_type_id = "Part"`
- No `DOC_*`, `DRAWING_OF`, or `PACKAGE` relationship type is seeded in WP1.1.
- No router, route-count, schema migration, or table change.

## Implementation

- `src/yuantus/seeder/meta/schemas.py`
  - Adds `_ensure_part_relationship_item_type(...)`.
  - Calls it from `MetaSchemaSeeder.run()` for `ASSEMBLY` and `REFERENCE`.
  - Corrects existing stale rows to strict Part-to-Part semantics on rerun.
- `src/yuantus/meta_engine/tests/test_pdm_relationship_types.py`
  - Verifies seed creation, idempotency, endpoint correction, Part-to-Part
    relationship creation/querying, non-Part rejection, and no forbidden
    Document-centric relationship types.
- `.github/workflows/ci.yml` and `conftest.py`
  - Add the new test to the contracts job and no-DB allowlist.
- `pyproject.toml` and `requirements.lock`
  - Declare the existing seeder dependency on `Faker`.
  - This is not new WP1.1 business behavior; it makes the already-imported
    seeder package reproducible in CI and local clean environments.

## Verification

Run in an isolated Python 3.11 venv created from `/opt/homebrew/bin/python3.11`,
with `requirements.lock` plus `pytest`:

- `python -m pytest -q src/yuantus/meta_engine/tests/test_pdm_relationship_types.py`
  - 5 passed
- `python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py`
  - 1 passed
- `python -m compileall -q src/yuantus/seeder/meta/schemas.py src/yuantus/meta_engine/tests/test_pdm_relationship_types.py`
  - passed
- `git diff --check`
  - clean

## Notes

- WP1.1 intentionally does not implement WP1.2 traversal APIs.
- WP1.1 intentionally does not implement WP1.3 2D/3D staleness.
- `ItemType` has no `is_polymorphic` column; for ItemType-backed
  relationships, `RelationshipService` already enforces strict endpoint type
  checks. This matches the WP1.0 Part-to-Part lock.
