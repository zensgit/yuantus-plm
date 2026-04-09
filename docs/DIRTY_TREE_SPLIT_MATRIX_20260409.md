# Dirty Tree Split Matrix

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This is the single-entry overview for the dirty-tree split sequence.

## Matrix

| Order | Domain | Suggested Branch | Suggested Commit Title | Primary Entry |
|---|---|---|---|---|
| 1 | `subcontracting` | `feature/subcontracting-split` | `feat(subcontracting): split approval role mapping cleanup cluster` | `bash scripts/print_subcontracting_first_cut_anchors.sh --branch-plan` |
| 2 | `docs-parallel` | `docs/parallel-artifact-pack` | `docs(parallel): split verification artifact pack` | `bash scripts/print_docs_parallel_split_helper.sh --branch-plan` |
| 3 | `cross-domain-services` | `feature/cross-domain-followups` | `feat(meta-engine): split cross-domain service followups` | `bash scripts/print_cross_domain_services_split_helper.sh --branch-plan` |
| 4 | `migrations` | `feature/domain-migrations-followup` | `db: split dirty-tree migration set` | `bash scripts/print_dirty_tree_domain_commands.sh --domain migrations --commit-plan` |
| 5 | `strict-gate` | `chore/strict-gate-followups` | `chore(strict-gate): split runner and contract updates` | `bash scripts/print_strict_gate_split_helper.sh --branch-plan` |
| 6 | `delivery-pack` | `docs/delivery-pack-followup` | `docs(delivery): split handoff package updates` | `bash scripts/print_delivery_pack_split_helper.sh --branch-plan` |

## Fast Commands

```bash
bash scripts/print_dirty_tree_split_matrix.sh
bash scripts/print_dirty_tree_split_matrix.sh --commands
bash scripts/print_dirty_tree_domain_coverage.sh
bash scripts/print_dirty_tree_domain_coverage.sh --unassigned
```

## Coverage Check

Before opening a new split branch, run the dirty-tree coverage helper once to see
whether the current dirty paths are already assigned to one of the six declared
domains or still sitting in the residual gap list.

- `bash scripts/print_dirty_tree_domain_coverage.sh`
- `bash scripts/print_dirty_tree_domain_coverage.sh --by-domain`
- `bash scripts/print_dirty_tree_domain_coverage.sh --unassigned`

## Related References

- `docs/DIRTY_TREE_SPLIT_ORDER_20260409.md`
- `docs/DIRTY_TREE_DOMAIN_COVERAGE_20260409.md`
- `docs/SUBCONTRACTING_SPLIT_EXECUTION_CARD_20260409.md`
- `docs/DOCS_PARALLEL_SPLIT_EXECUTION_CARD_20260409.md`
- `docs/CROSS_DOMAIN_SERVICES_SPLIT_EXECUTION_CARD_20260409.md`
- `docs/STRICT_GATE_SPLIT_EXECUTION_CARD_20260409.md`
- `docs/DELIVERY_PACK_SPLIT_EXECUTION_CARD_20260409.md`
