# Dirty Tree Domain Coverage

Date: `2026-04-09`  
Branch: `feature/claude-c43-cutted-parts-throughput`

This note captures the first dirty-tree coverage pass after the six split
domains were declared.

## Snapshot

Command:

```bash
bash scripts/print_dirty_tree_domain_coverage.sh
```

Observed coverage snapshot:

- total dirty paths: `504`
- assigned dirty paths: `492`
- unassigned dirty paths: `12`
- coverage gap present: `yes`

This `504 / 492 / 12` snapshot was taken before the coverage helper itself,
its doc, and its contract wiring were added. While those helper files are still
dirty in the working tree, the live command can temporarily report a larger
residual gap (for example `17`) without meaning that the original six domain
assignments regressed.

Per-domain counts from `bash scripts/print_dirty_tree_domain_coverage.sh --by-domain`:

- `subcontracting`: `361`
- `docs-parallel`: `91`
- `cross-domain-services`: `39`
- `migrations`: `4`
- `strict-gate`: `5`
- `delivery-pack`: `7`

## Residual Gap

Current uncovered paths:

- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md`
- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md`
- `docs/GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md`
- `docs/PRODUCT_SKU_MATRIX.md`
- `docs/WORKFLOW_OWNERSHIP_RULES.md`
- `scripts/print_dirty_tree_domain_coverage.sh`
- `src/yuantus/meta_engine/tests/test_box_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py`
- `src/yuantus/meta_engine/tests/test_router_registration_misc.py`
- `src/yuantus/meta_engine/web/app_router.py`
- `src/yuantus/meta_engine/web/manufacturing_router.py`

## Residual Clusters

The smallest reasonable clustering for the residual gap is:

1. `router-surface-misc`
   `src/yuantus/meta_engine/web/app_router.py`, `src/yuantus/meta_engine/web/manufacturing_router.py`, and the four router-registration/router-surface tests.
   Rationale: router wiring and router tests should travel together as one surface-area cleanup.
2. `subcontracting-governance-docs`
   The two `DEV_AND_VERIFICATION_SUBCONTRACTING_*` docs plus `docs/GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md`.
   Rationale: they are governance/runbook artifacts that do not belong in the code-facing subcontracting split.
3. `product-strategy-docs`
   `docs/PRODUCT_SKU_MATRIX.md` and `docs/WORKFLOW_OWNERSHIP_RULES.md`.
   Rationale: they define cross-product packaging and workflow ownership policy, not a code domain.
4. `dirty-tree-tooling`
   `scripts/print_dirty_tree_domain_coverage.sh`.
   Rationale: standalone repo-maintenance helper with no product-domain ownership.

## Recommended Use

Run the helper before and after every split:

```bash
bash scripts/print_dirty_tree_domain_coverage.sh
bash scripts/print_dirty_tree_domain_coverage.sh --by-domain
bash scripts/print_dirty_tree_domain_coverage.sh --unassigned
```

Do not create a seventh cleanup domain yet. Keep the residual paths explicit
until one of the four residual clusters grows large enough to justify its own
branch plan.
