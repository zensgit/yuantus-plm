# Split Branches Summary

Date: `2026-04-09`
Source branch: `feature/claude-c43-cutted-parts-throughput`

This note summarizes the three residual split branches that were extracted from
the dirty-tree residual pool without widening the main branch scope.

## Extracted Branches

1. `feature/router-surface-misc`
   - commit: `548a9b3`
   - title: `fix(routers): align app prefix and routing 404 handling`
   - scope:
     - `src/yuantus/meta_engine/web/app_router.py`
     - `src/yuantus/meta_engine/web/manufacturing_router.py`
     - `src/yuantus/meta_engine/tests/test_box_router.py`
     - `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
     - `src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py`
2. `docs/subcontracting-governance-pack`
   - commit: `f1235c8`
   - title: `docs(subcontracting): split governance and operator pack`
   - scope:
     - `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md`
     - `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md`
     - `docs/GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md`
3. `docs/product-strategy-pack`
   - commit: `ffd9398`
   - title: `docs(product): split sku and workflow ownership pack`
   - scope:
     - `docs/PRODUCT_SKU_MATRIX.md`
     - `docs/WORKFLOW_OWNERSHIP_RULES.md`

## Why This Matters

- the main branch keeps its existing reviewer scope
- residual work is no longer purely theoretical; three real split branches now
  exist on origin
- the residual execution cards have been validated as actionable, not just
  descriptive

## Residual Rule

Do **not** define a seventh split domain.

The extraction work proved that the remaining residual paths are better handled
as targeted split branches than as a new generalized domain.

## References

- `docs/DIRTY_TREE_RESIDUAL_CLOSEOUT_20260409.md`
- `docs/DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md`
- `docs/ROUTER_SURFACE_MISC_SPLIT_EXECUTION_CARD_20260409.md`
- `docs/SUBCONTRACTING_GOVERNANCE_DOCS_SPLIT_EXECUTION_CARD_20260409.md`
- `docs/PRODUCT_STRATEGY_DOCS_SPLIT_EXECUTION_CARD_20260409.md`
