#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_delivery_pack_split_helper.sh [--git-add-cmd] [--branch-plan]

Options:
  --git-add-cmd  Print the exact git add command for the delivery-pack split.
  --branch-plan  Print the one-page execution note for the delivery-pack split.
  -h, --help     Show help.

Default output:
  Prints the included handoff/package docs and CONTRIBUTING.md for the delivery-pack split.
EOF
}

PRINT_GIT_ADD_CMD="false"
PRINT_BRANCH_PLAN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --git-add-cmd)
      PRINT_GIT_ADD_CMD="true"
      shift
      ;;
    --branch-plan)
      PRINT_BRANCH_PLAN="true"
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

selected_count=0
for flag in "${PRINT_GIT_ADD_CMD}" "${PRINT_BRANCH_PLAN}"; do
  if [[ "${flag}" == "true" ]]; then
    selected_count=$((selected_count + 1))
  fi
done

if [[ "${selected_count}" -gt 1 ]]; then
  echo "ERROR: choose only one of --git-add-cmd or --branch-plan" >&2
  exit 2
fi

PATHS=(
  "CONTRIBUTING.md"
  "docs/DELIVERY_DOC_INDEX.md"
  "docs/DELIVERY_EXTERNAL_HANDOFF_GUIDE_20260203.md"
  "docs/DELIVERY_EXTERNAL_VERIFY_COMMANDS_20260203.md"
  "docs/DELIVERY_PACKAGE_HASHES_20260203.md"
  "docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt"
  "docs/DELIVERY_PACKAGE_NOTE_20260203.md"
)

print_git_add_cmd() {
  printf 'git add --'
  for rel in "${PATHS[@]}"; do
    printf ' \\\n  %q' "${rel}"
  done
  printf '\n'
}

if [[ "${PRINT_GIT_ADD_CMD}" == "true" ]]; then
  print_git_add_cmd
  exit 0
fi

if [[ "${PRINT_BRANCH_PLAN}" == "true" ]]; then
  cat <<'EOF'
Delivery-pack branch execution note:

Suggested branch:
- docs/delivery-pack-followup

Suggested commit title:
- docs(delivery): split handoff package updates

Step 1: inspect scope
- bash scripts/print_dirty_tree_domain_commands.sh --domain delivery-pack --status
- bash scripts/print_dirty_tree_domain_commands.sh --domain delivery-pack --commit-plan

Step 2: stage the delivery pack
EOF
  print_git_add_cmd
  cat <<'EOF'

Step 3: review staged result
- git diff --cached --stat
- git diff --cached -- CONTRIBUTING.md
- git diff --cached -- docs/DELIVERY_DOC_INDEX.md
- git diff --cached -- docs/DELIVERY_EXTERNAL_HANDOFF_GUIDE_20260203.md
- git diff --cached -- docs/DELIVERY_PACKAGE_NOTE_20260203.md

Rule:
- keep strict-gate out
- keep docs-parallel out
- keep code-facing domains out
- this split is documentation/package only; do not widen it with code or migration changes
EOF
  exit 0
fi

cat <<'EOF'
Delivery-pack split helper:

Includes:
- CONTRIBUTING.md
- docs/DELIVERY_DOC_INDEX.md
- docs/DELIVERY_EXTERNAL_HANDOFF_GUIDE_20260203.md
- docs/DELIVERY_EXTERNAL_VERIFY_COMMANDS_20260203.md
- docs/DELIVERY_PACKAGE_HASHES_20260203.md
- docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt
- docs/DELIVERY_PACKAGE_NOTE_20260203.md

Excludes:
- strict-gate
- docs-parallel
- cross-domain-services
- subcontracting
- migrations

Fast commands:
- bash scripts/print_delivery_pack_split_helper.sh --git-add-cmd
- bash scripts/print_delivery_pack_split_helper.sh --branch-plan
EOF
