# DEV & Verification: OdooPLM 19 CAD-PDM WP1.2 bounded flat projection

Date: 2026-06-09

Implements the bounded-flat follow-up locked by
`DEVELOPMENT_WP1_2_BOUNDED_FLAT_TASKBOOK_20260609.md`.

## Scope

- `relationship-tree?projection=flat` now uses a direct flat projection helper
  instead of building the duplicate-preserving tree first.
- `projection=tree` is unchanged: shared parts still materialize under every
  parent path and still use `MAX_TRAVERSAL_NODES`.
- No route, schema, migration, stale-drawings, pack-and-go, or lifecycle changes.
  Route-count baseline stays 707.

## Semantics

- `occurrence_count` is a distinct non-cycle ASSEMBLY relationship-edge path
  count. Parallel ASSEMBLY relationship rows count as distinct occurrences.
- Cycle re-entry contributes zero and does not descend; other non-cycle paths to
  the same item remain countable.
- `first_path`, `first_relationship_path`, and `min_depth` keep the shortest-first
  traversal behavior.
- Outgoing edge rows are cached per item to avoid repeated DB queries while still
  preserving exact per-path contributions.

## Verification

Focused traversal tests:

```bash
PYTHONPATH=src .venv-wp13/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_pdm_relationship_traversal.py
# 20 passed
```

Added/updated coverage:

- flat no longer consumes the duplicate-tree node budget on stacked diamonds;
- stacked-diamond descendants keep exact path-count contributions;
- parallel ASSEMBLY edge rows count as distinct occurrences;
- cycle edges contribute zero and terminate;
- router `projection=flat` no longer trips the tree budget.

## Non-goals

- No general O(V+E) claim for exact path-count flat projection.
- No global visited rewrite for tree projection.
- No B2b assembly-promotion implementation.
