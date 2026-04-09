# Split Branch PR Drafts

Date: `2026-04-09`
Source branch: `feature/claude-c43-cutted-parts-throughput`

This note collects reviewer-facing PR title/body drafts for the three residual
split branches already pushed to origin.

## PR 1

- branch: `feature/router-surface-misc`
- commit: `548a9b3`
- suggested title: `fix(routers): align app prefix and routing 404 handling`

Suggested body:

- aligns `app_router` to the mounted `/api/v1/apps/*` surface by fixing the router prefix
- converts routing calculate-time and calculate-cost missing-routing failures into HTTP 404s
- adds focused regression coverage in `box`, `cutted_parts`, and `manufacturing_routing` router tests
- keeps scope limited to 5 code/test files extracted from the residual dirty-tree pool
- verification: `pytest src/yuantus/meta_engine/tests/test_box_router.py src/yuantus/meta_engine/tests/test_cutted_parts_router.py src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py -q`

## PR 2

- branch: `docs/subcontracting-governance-pack`
- commit: `f1235c8`
- suggested title: `docs(subcontracting): split governance and operator pack`

Suggested body:

- extracts the subcontracting launch checklist, operator runbook, and governance reading guide into a clean doc-only branch
- keeps governance/operator guidance separate from the code-facing `subcontracting` split
- reduces reviewer noise on the main branch by removing three residual governance docs from the shared dirty tree
- scope is strictly limited to the three docs listed in the execution card

## PR 3

- branch: `docs/product-strategy-pack`
- commit: `ffd9398`
- suggested title: `docs(product): split sku and workflow ownership pack`

Suggested body:

- extracts `PRODUCT_SKU_MATRIX.md` and `WORKFLOW_OWNERSHIP_RULES.md` into a dedicated product-strategy doc branch
- keeps packaging/ownership policy separate from router and subcontracting follow-up branches
- turns the last doc-only residual strategy pair into an independently reviewable PR
- scope is strictly limited to the two strategy docs listed in the execution card

## References

- `docs/SPLIT_BRANCHES_SUMMARY_20260409.md`
- `docs/DIRTY_TREE_RESIDUAL_CLOSEOUT_20260409.md`
- `docs/ROUTER_SURFACE_MISC_SPLIT_EXECUTION_CARD_20260409.md`
- `docs/SUBCONTRACTING_GOVERNANCE_DOCS_SPLIT_EXECUTION_CARD_20260409.md`
- `docs/PRODUCT_STRATEGY_DOCS_SPLIT_EXECUTION_CARD_20260409.md`
