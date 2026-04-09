#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_dirty_tree_split_matrix.sh [--commands]

Options:
  --commands  Print the fastest execution command for each split domain.
  -h, --help  Show help.

Default output:
  Prints the dirty-tree split matrix with order, branch, commit title, and
  primary helper entrypoint for each domain.
EOF
}

PRINT_COMMANDS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --commands)
      PRINT_COMMANDS="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "${PRINT_COMMANDS}" == "true" ]]; then
  cat <<'EOF'
1. subcontracting
   bash scripts/print_subcontracting_first_cut_anchors.sh --branch-plan
2. docs-parallel
   bash scripts/print_docs_parallel_split_helper.sh --branch-plan
3. cross-domain-services
   bash scripts/print_cross_domain_services_split_helper.sh --branch-plan
4. migrations
   bash scripts/print_dirty_tree_domain_commands.sh --domain migrations --commit-plan
5. strict-gate
   bash scripts/print_strict_gate_split_helper.sh --branch-plan
6. delivery-pack
   bash scripts/print_delivery_pack_split_helper.sh --branch-plan
EOF
  exit 0
fi

cat <<'EOF'
Dirty-tree split matrix:

1. subcontracting
   branch: feature/subcontracting-split
   title: feat(subcontracting): split approval role mapping cleanup cluster
   entry: bash scripts/print_subcontracting_first_cut_anchors.sh --branch-plan

2. docs-parallel
   branch: docs/parallel-artifact-pack
   title: docs(parallel): split verification artifact pack
   entry: bash scripts/print_docs_parallel_split_helper.sh --branch-plan

3. cross-domain-services
   branch: feature/cross-domain-followups
   title: feat(meta-engine): split cross-domain service followups
   entry: bash scripts/print_cross_domain_services_split_helper.sh --branch-plan

4. migrations
   branch: feature/domain-migrations-followup
   title: db: split dirty-tree migration set
   entry: bash scripts/print_dirty_tree_domain_commands.sh --domain migrations --commit-plan

5. strict-gate
   branch: chore/strict-gate-followups
   title: chore(strict-gate): split runner and contract updates
   entry: bash scripts/print_strict_gate_split_helper.sh --branch-plan

6. delivery-pack
   branch: docs/delivery-pack-followup
   title: docs(delivery): split handoff package updates
   entry: bash scripts/print_delivery_pack_split_helper.sh --branch-plan
EOF
