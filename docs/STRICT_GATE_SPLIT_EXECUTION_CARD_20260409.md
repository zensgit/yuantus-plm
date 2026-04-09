# Strict-Gate Split Execution Card

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This card is the fastest safe ops/runtime split after the larger domain slices
have been isolated.

## Why this is later

- smaller than the main code-facing domains
- important operationally, but not the main PR-scope hazard
- best reviewed as a focused runner/runtime follow-up

## Execute

```bash
git switch -c chore/strict-gate-followups
bash scripts/print_dirty_tree_domain_commands.sh --domain strict-gate --status
bash scripts/print_dirty_tree_domain_commands.sh --domain strict-gate --commit-plan
bash scripts/print_strict_gate_split_helper.sh
bash scripts/print_strict_gate_split_helper.sh --git-add-cmd
bash scripts/print_strict_gate_split_helper.sh --branch-plan
```

## Rule

- do **not** mix delivery-pack into this split
- do **not** mix docs-parallel or cross-domain-services into this split
- keep this slice limited to strict-gate runners, reports, and their owning tests

## Related references

- `docs/DIRTY_TREE_SPLIT_ORDER_20260409.md`
- `scripts/print_dirty_tree_domain_commands.sh`
- `scripts/print_strict_gate_split_helper.sh`
