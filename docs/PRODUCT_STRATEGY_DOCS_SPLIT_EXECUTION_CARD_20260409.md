# Product-Strategy-Docs Split Execution Card

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This card is the last residual doc-only cleanup in the current dirty-tree
coverage gap.

## Scope

Target files:

- `docs/PRODUCT_SKU_MATRIX.md`
- `docs/WORKFLOW_OWNERSHIP_RULES.md`

## Execute

```bash
git switch -c docs/product-strategy-pack
git status --short -- \
  docs/PRODUCT_SKU_MATRIX.md \
  docs/WORKFLOW_OWNERSHIP_RULES.md
git add -- \
  docs/PRODUCT_SKU_MATRIX.md \
  docs/WORKFLOW_OWNERSHIP_RULES.md
git diff --cached --stat
```

## Review

```bash
git diff --cached -- \
  docs/PRODUCT_SKU_MATRIX.md \
  docs/WORKFLOW_OWNERSHIP_RULES.md
```

## Suggested Commit

- branch: `docs/product-strategy-pack`
- commit title: `docs(product): split sku and workflow ownership pack`

## Rule

- keep this split doc-only
- do **not** mix subcontracting governance docs into this branch
- do **not** mix router-surface residual files into this branch
- keep SKU matrix and workflow ownership rules together as one strategy packet

## Related References

- `docs/DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md`
- `docs/DIRTY_TREE_DOMAIN_COVERAGE_20260409.md`
- `docs/BRANCH_CLOSEOUT_SUMMARY_20260409.md`
