# Dirty Tree Residual Closeout

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This note is the one-page operator closeout for the current dirty-tree residual
gap after the six declared split domains and their execution helpers landed.

## Baseline

Current live baseline from:

```bash
bash scripts/print_dirty_tree_domain_coverage.sh
bash scripts/print_dirty_tree_domain_coverage.sh --unassigned
```

Current numbers:

- total dirty paths: `503`
- assigned dirty paths: `492`
- unassigned dirty paths: `11`

## Residual Clusters

The remaining residual work is fully reduced to three explicit clusters:

1. `router-surface-misc`
   - execution card:
     `docs/ROUTER_SURFACE_MISC_SPLIT_EXECUTION_CARD_20260409.md`
2. `subcontracting-governance-docs`
   - execution card:
     `docs/SUBCONTRACTING_GOVERNANCE_DOCS_SPLIT_EXECUTION_CARD_20260409.md`
3. `product-strategy-docs`
   - execution card:
     `docs/PRODUCT_STRATEGY_DOCS_SPLIT_EXECUTION_CARD_20260409.md`

## Domain Rule

Do **not** define a seventh split domain.

The residual set is now small and explicit enough that extra domain machinery
would add naming overhead without reducing risk.

## Fast Path

Use exactly one of these cards next:

```bash
sed -n '1,220p' docs/ROUTER_SURFACE_MISC_SPLIT_EXECUTION_CARD_20260409.md
sed -n '1,220p' docs/SUBCONTRACTING_GOVERNANCE_DOCS_SPLIT_EXECUTION_CARD_20260409.md
sed -n '1,220p' docs/PRODUCT_STRATEGY_DOCS_SPLIT_EXECUTION_CARD_20260409.md
```

## References

- `docs/DIRTY_TREE_DOMAIN_COVERAGE_20260409.md`
- `docs/DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md`
- `docs/DIRTY_TREE_SPLIT_MATRIX_20260409.md`
