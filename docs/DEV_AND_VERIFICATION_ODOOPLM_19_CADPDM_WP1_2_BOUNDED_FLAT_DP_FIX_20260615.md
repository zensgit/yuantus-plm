# DEV & Verification: WP1.2 bounded-flat — memoized-DP fix (regression repair)

Date: 2026-06-15

Repairs a **HIGH-severity unbounded-traversal regression** introduced by the
bounded-flat impl (#748, taskbook
`DEVELOPMENT_WP1_2_BOUNDED_FLAT_TASKBOOK_20260609.md`). Read-only projection change;
**no route, no migration, no schema, no public response-shape change.**

## The bug (confirmed in merged `main`)

`RelationshipService.get_relationship_tree(projection="flat")` delegated to
`_build_flat_projection`, which **enumerated every distinct non-cycle path** — each
BFS queue entry was a full path tuple `(item_id, depth, path, rel_path)` concatenated
on every enqueue. For a heavily-shared assembly the path count is *exponential* in
depth (a 25-deep stacked diamond has 2²⁵ ≈ 33.5M paths), so the queue/memory blew up
with **no `TraversalBudgetError` guard** — `_build_flat_projection` took neither
`max_nodes` nor any counter. This was a regression: before #748, flat went through
`_build_node`, which carried the 50 000-node `MAX_TRAVERSAL_NODES` budget, so flat was
bounded. After #748 it was bounded only by `max_depth` × branching — i.e. effectively
unbounded, a memory-exhaustion / DoS vector on the exact "large shared-part assembly"
input the taskbook §1 set out to make *succeed*.

This is the failure mode flagged at taskbook review: an implementer reading D6
("path-local cycle suppression") literally and writing path-carrying enumeration,
reintroducing the exponential blowup the slice existed to remove.

## The fix — memoized topological DP (genuinely bounded, semantics-preserving)

`_build_flat_projection` is rewritten as three linear passes, **no path enumeration**:

1. **Shortest-first BFS** → reachable set, `min_depth` / `first_path` /
   `first_relationship_path` (first discovery wins, edge-order tie-break), and recorded
   adjacency.
2. **DFS dropping back-edges** (an edge to an ancestor still on the current DFS path —
   the path-based cycle rule) → a DAG + finish order.
3. **Depth-stratified DP** in topological (reverse-finish) order:
   `count(v)[d+1] += count(u)[d]` per edge `u→v`, capped at `max_depth`;
   `occurrence_count(v) = Σ_d count(v)[d]`. Parallel edges between the same pair are
   counted as distinct occurrences (the DP iterates edges, not unique parents).

Complexity: **O(V·max_depth + E)** time and memory. `occurrence_count` may now be a
large integer (e.g. 2²⁵) for a deeply-shared part, but it is *computed* cheaply via DP
rather than enumerated — which is exactly the "bounded, returns where the tree raises"
guarantee the taskbook wanted.

**No budget guard is added (by design).** The existing contracts
`test_flat_no_longer_uses_duplicate_tree_budget` (`max_nodes=5`) and
`test_router_flat_projection_does_not_use_tree_budget` (`MAX_TRAVERSAL_NODES=5`
monkeypatched) assert flat **does not raise** on a 7-node graph. The DP makes flat
bounded *by construction* (size of the deduped item set × depth), so it correctly
ignores the tree-node budget — adding a `max_nodes`-keyed guard would both break those
contracts and contradict the taskbook goal.

## Verification (Python 3.11, no-DB)

- `test_pdm_relationship_traversal.py` → **21 passed**. All prior semantics preserved
  exactly: diamond dedupe (D=2), stacked-diamond counts (C=2, D1=D2=2, E=4) with
  `first_path = ["A","B1","C","D1","E"]`, parallel-edge occurrences (B=2, first rel
  edge), cycle edge contributes zero (A=B=C=1), and the two "flat ignores the tree
  budget" contracts.
- **New regression guard** `test_flat_deep_stacked_diamond_is_bounded_not_enumerated`:
  25 chained diamonds (2²⁵ = 33 554 432 paths to the sink) → `occurrence_count(L25) ==
  2²⁵`, `m{i}a == 2ⁱ`, `min_depth(L25) == 50`, completing in milliseconds. Reverting to
  enumeration makes this test hang / OOM — the guard #748 lacked.
- Blast radius: the **only** caller of `get_relationship_tree`/flat is
  `pdm_relationship_router`; B2b `AssemblyPromotionService` and pack-and-go use the
  separate `get_reachable_items` visited-set BFS (untouched). `test_pdm_relationship_*`
  + `test_assembly_promotion_service` + `test_plugin_pack_and_go` → **50 passed**.
- `create_app()` route count unchanged at **709** (no route added). Test file already
  registered in `ci.yml`.

## Not in this PR

- No new public response field; `occurrence_count` / `first_path` semantics unchanged.
- No change to tree projection, `get_reachable_items`, stale-drawings, B2b, or
  pack-and-go.
- No `?status=`-style API additions.
