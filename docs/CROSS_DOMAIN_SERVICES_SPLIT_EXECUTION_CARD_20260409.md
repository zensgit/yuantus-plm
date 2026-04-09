# Cross-Domain-Services Split Execution Card

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This card is the fastest safe code-facing split after `subcontracting` and the
`docs-parallel` doc pack.

## Why this is later

- it still spans multiple product areas
- it mixes code, tests, docs, and migrations
- it should follow the subcontracting spike and the docs-parallel noise cleanup

## Execute

```bash
git switch -c feature/cross-domain-followups
bash scripts/print_dirty_tree_domain_commands.sh --domain cross-domain-services --status
bash scripts/print_dirty_tree_domain_commands.sh --domain cross-domain-services --commit-plan
bash scripts/print_cross_domain_services_split_helper.sh
bash scripts/print_cross_domain_services_split_helper.sh --git-add-cmd
bash scripts/print_cross_domain_services_split_helper.sh --branch-plan
```

## Rule

- do **not** mix `docs-parallel` into this split
- do **not** reopen `subcontracting`
- keep this domain’s migrations and reading guides with the owning code

## Related references

- `docs/POST_SUBCONTRACTING_NEXT_STEP_20260409.md`
- `docs/DIRTY_TREE_SPLIT_ORDER_20260409.md`
- `scripts/print_dirty_tree_domain_commands.sh`
- `scripts/print_cross_domain_services_split_helper.sh`
