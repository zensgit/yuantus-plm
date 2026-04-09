# Docs-Parallel Split Execution Card

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This card is the fastest safe second split after the first `subcontracting`
cut lands.

## Why this is next

- largest remaining reviewer noise after subcontracting
- mostly documentation bulk rather than monolithic code paths
- reduces PR clutter before any `cross-domain-services` code split

## Execute

```bash
git switch -c docs/parallel-artifact-pack
bash scripts/print_dirty_tree_domain_commands.sh --domain docs-parallel --status
bash scripts/print_dirty_tree_domain_commands.sh --after-first-cut
bash scripts/print_docs_parallel_split_helper.sh
bash scripts/print_docs_parallel_split_helper.sh --git-add-cmd
bash scripts/print_docs_parallel_split_helper.sh --branch-plan
```

## Rule

- do **not** mix `cross-domain-services` into this split
- do **not** pull back in `subcontracting`-specific docs
- use the exact pathspec command; do **not** use `git add .`

## Related references

- `docs/POST_SUBCONTRACTING_NEXT_STEP_20260409.md`
- `docs/DIRTY_TREE_SPLIT_ORDER_20260409.md`
- `scripts/print_dirty_tree_domain_commands.sh`
- `scripts/print_docs_parallel_split_helper.sh`
