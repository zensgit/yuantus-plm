#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_subcontracting_first_cut_anchors.sh [--grep]

Options:
  --grep     Print ready-to-run grep commands for the first subcontracting cut.
  -h, --help Show help.

Default output:
  Prints the likely files and anchor tokens for the approval role mapping
  cleanup cluster inside the subcontracting domain.
EOF
}

PRINT_GREP="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --grep)
      PRINT_GREP="true"
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

TOKENS=(
  "approval_role_mapping"
  "cleanup_policy"
  "cleanup_history"
  "role_mapping_registry"
  "role_mapping_policy_board"
  "role_mapping_cleanup_board"
)

FILES=(
  "src/yuantus/meta_engine/subcontracting/service.py"
  "src/yuantus/meta_engine/web/subcontracting_router.py"
  "src/yuantus/meta_engine/tests/test_subcontracting_service.py"
  "src/yuantus/meta_engine/tests/test_subcontracting_router.py"
  "migrations/versions/b3c4d5e6f7a8_add_subcontract_approval_role_mappings.py"
  "docs/APPROVAL_ROLE_MAPPING_CLEANUP_CONTRACT_SURPASS_READING_GUIDE_20260401.md"
)

if [[ "${PRINT_GREP}" == "true" ]]; then
  printf 'rg -n "'
  sep=""
  for token in "${TOKENS[@]}"; do
    printf '%s%s' "${sep}" "${token}"
    sep="|"
  done
  printf '"'
  for file in "${FILES[@]}"; do
    printf ' \\\n  %q' "${file}"
  done
  printf '\n'
  exit 0
fi

cat <<'EOF'
First subcontracting cut:
  approval role mapping cleanup cluster

Likely files to touch first:
EOF

for file in "${FILES[@]}"; do
  printf -- '- %s\n' "${file}"
done

cat <<'EOF'

Anchor tokens:
- approval_role_mapping
- cleanup_policy
- cleanup_history
- role_mapping_registry
- role_mapping_policy_board
- role_mapping_cleanup_board

Recommended staging mode:
- inspect with grep first
- stage with `git add -p`, not `git add .`
- keep this incision isolated from vendor message / receipt / return flows
EOF
