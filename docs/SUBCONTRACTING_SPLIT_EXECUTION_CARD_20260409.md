# Subcontracting Split Execution Card

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This card is the fastest safe next step for the current dirty tree.

## Why this is first

- largest dirty domain by far
- clearest accidental PR scope-creep source
- roughly `72,000+` lines across service, router, tests, and dedicated docs

## Execute

```bash
git switch -c feature/subcontracting-split
bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --status
bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --commit-plan
```

## Preferred first incision

Claude Code read-only sidecar recommends starting with the approval role
mapping cleanup cluster inside `SubcontractingService`, because it is the
lowest-risk self-contained slice relative to the rest of the subcontracting
domain.

## Rule

- do **not** use `git add .`
- do **not** mix `docs-parallel` or `cross-domain-services` into this split
- keep the migrations listed by the helper with the subcontracting split

## Related references

- `docs/DIRTY_TREE_DOMAIN_INVENTORY_20260409.md`
- `docs/DIRTY_TREE_SPLIT_ORDER_20260409.md`
- `scripts/print_dirty_tree_domain_commands.sh`
