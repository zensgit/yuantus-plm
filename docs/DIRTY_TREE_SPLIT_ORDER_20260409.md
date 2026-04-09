# Dirty Tree Split Order

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This note converts the dirty-tree inventory into an execution order. It is
meant for safe cleanup sequencing, not for widening the current reviewer scope.

## Recommended order

| Order | Domain | Why first / later | Helper command |
|---|---|---|---|
| 1 | `subcontracting` | Largest risk by far: ~72k lines and the clearest accidental-scope center. | `bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --commit-plan` |
| 2 | `docs-parallel` | 400+ parallel design / verification docs create major review noise even when code is untouched. | `bash scripts/print_dirty_tree_domain_commands.sh --domain docs-parallel --commit-plan` |
| 3 | `cross-domain-services` | Remaining approvals / ECO / document-sync / parallel-task spillover should be handled after the main spike is isolated. | `bash scripts/print_dirty_tree_domain_commands.sh --domain cross-domain-services --commit-plan` |
| 4 | `migrations` | Migrations should follow their owning domain and not be stranded as an orphaned tail. | `bash scripts/print_dirty_tree_domain_commands.sh --domain migrations --commit-plan` |
| 5 | `strict-gate` | Small CI/operator follow-up domain; important, but not the main PR-scope hazard. | `bash scripts/print_dirty_tree_domain_commands.sh --domain strict-gate --commit-plan` |
| 6 | `delivery-pack` | Lowest code risk. Packaging / handoff docs should be finalized last. | `bash scripts/print_dirty_tree_domain_commands.sh --domain delivery-pack --commit-plan` |

## Fast start

```bash
bash scripts/print_dirty_tree_split_matrix.sh
bash scripts/print_dirty_tree_domain_commands.sh --first-step
bash scripts/print_dirty_tree_domain_commands.sh --after-first-cut
bash scripts/print_dirty_tree_domain_commands.sh --recommended-order
bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --status
bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --commit-plan
```

Execution card:
`docs/SUBCONTRACTING_SPLIT_EXECUTION_CARD_20260409.md`

Second-step note:
`docs/POST_SUBCONTRACTING_NEXT_STEP_20260409.md`

Matrix overview:
`docs/DIRTY_TREE_SPLIT_MATRIX_20260409.md`

## Rule

Do not use `git add .` while this tree is still mixed. Always stage by domain.
