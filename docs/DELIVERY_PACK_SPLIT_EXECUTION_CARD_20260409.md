# Delivery-Pack Split Execution Card

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This card is the fastest safe final split for the dirty-tree cleanup sequence.

## Why this is last

- lowest code risk
- pure documentation / handoff packaging
- easiest domain to review after code-facing and ops-facing splits are isolated

## Execute

```bash
git switch -c docs/delivery-pack-followup
bash scripts/print_dirty_tree_domain_commands.sh --domain delivery-pack --status
bash scripts/print_dirty_tree_domain_commands.sh --domain delivery-pack --commit-plan
bash scripts/print_delivery_pack_split_helper.sh
bash scripts/print_delivery_pack_split_helper.sh --git-add-cmd
bash scripts/print_delivery_pack_split_helper.sh --branch-plan
```

## Rule

- do **not** mix strict-gate into this split
- do **not** mix docs-parallel or code-facing domains into this split
- keep this slice limited to package / handoff documentation and `CONTRIBUTING.md`

## Related references

- `docs/DIRTY_TREE_SPLIT_ORDER_20260409.md`
- `scripts/print_dirty_tree_domain_commands.sh`
- `scripts/print_delivery_pack_split_helper.sh`
