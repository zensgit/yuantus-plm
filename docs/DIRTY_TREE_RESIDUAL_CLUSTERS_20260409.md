# Dirty Tree Residual Clusters

Date: `2026-04-09`  
Branch: `feature/claude-c43-cutted-parts-throughput`

This note tracks the live post-helper residual dirty-path gap after the six
declared split domains are applied.

## Live Snapshot

Commands:

```bash
bash scripts/print_dirty_tree_domain_coverage.sh
bash scripts/print_dirty_tree_domain_coverage.sh --unassigned
```

Current live snapshot:

- total dirty paths: `503`
- assigned dirty paths: `492`
- unassigned dirty paths: `11`

## Residual Clusters

The remaining uncovered paths cluster cleanly into three residual groups:

1. `router-surface-misc`
   - `src/yuantus/meta_engine/web/app_router.py`
   - `src/yuantus/meta_engine/web/manufacturing_router.py`
   - `src/yuantus/meta_engine/tests/test_box_router.py`
   - `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
   - `src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py`
   - `src/yuantus/meta_engine/tests/test_router_registration_misc.py`
   Rationale: shared router-wiring and router-surface tests should stay in one
   follow-up cleanup, not be spread across the existing code domains.
2. `subcontracting-governance-docs`
   - `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md`
   - `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md`
   - `docs/GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md`
   Rationale: governance/runbook artifacts are adjacent to subcontracting work
   but do not belong in the code-facing `subcontracting` split branch.
3. `product-strategy-docs`
   - `docs/PRODUCT_SKU_MATRIX.md`
   - `docs/WORKFLOW_OWNERSHIP_RULES.md`
   Rationale: these two docs describe cross-product packaging and ownership
   policy, not a code or operational domain.

## Domain Decision

Do **not** define a seventh split domain yet.

The residual set is small, stable, and heterogeneous. Keeping it explicit is
safer than inventing a new domain name that would blur the current six-domain
matrix.

## When To Revisit

Re-evaluate the domain matrix only if one of these happens:

- `router-surface-misc` gains more router/runtime files and becomes a stable
  code-facing branch scope
- the subcontracting governance docs grow into a standalone handoff package
- the product strategy docs expand into a larger packaging/governance pack
