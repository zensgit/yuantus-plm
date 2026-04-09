# Post-Subcontracting Next Step

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This note answers one question only: what to split next after the first
`subcontracting` cut lands cleanly.

## Recommended next domain

`docs-parallel`

Why:

- highest remaining review noise after subcontracting
- mostly documentation bulk, so it reduces PR clutter without reopening the
  largest code paths
- keeps `cross-domain-services` available as a later code-focused split

## Fast command path

```bash
bash scripts/print_dirty_tree_domain_commands.sh --after-first-cut
bash scripts/print_dirty_tree_domain_commands.sh --domain docs-parallel --status
bash scripts/print_dirty_tree_domain_commands.sh --domain docs-parallel --commit-plan
bash scripts/print_docs_parallel_split_helper.sh --branch-plan
```

## Fallback

If `docs-parallel` is intentionally deferred, the next code-facing fallback is:

`cross-domain-services`

```bash
bash scripts/print_dirty_tree_domain_commands.sh --domain cross-domain-services --status
bash scripts/print_dirty_tree_domain_commands.sh --domain cross-domain-services --commit-plan
```

## Rule

- do **not** mix `docs-parallel` with `cross-domain-services`
- do **not** reopen `subcontracting` in the same follow-up split

Execution card:
`docs/DOCS_PARALLEL_SPLIT_EXECUTION_CARD_20260409.md`
