#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_subcontracting_first_cut_anchors.sh [--grep] [--hunks]

Options:
  --grep     Print ready-to-run grep commands for the first subcontracting cut.
  --hunks    Print the recommended git-add-p hunk order for the first cut.
  -h, --help Show help.

Default output:
  Prints the likely files and anchor tokens for the approval role mapping
  cleanup cluster inside the subcontracting domain.
EOF
}

PRINT_GREP="false"
PRINT_HUNKS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --grep)
      PRINT_GREP="true"
      shift
      ;;
    --hunks)
      PRINT_HUNKS="true"
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

if [[ "${PRINT_GREP}" == "true" && "${PRINT_HUNKS}" == "true" ]]; then
  echo "ERROR: choose only one of --grep or --hunks" >&2
  exit 2
fi

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

if [[ "${PRINT_HUNKS}" == "true" ]]; then
  cat <<'EOF'
Recommended git add -p order for the first subcontracting cut:

1. Service scope helpers + CRUD seed
   service.py
   - 2962 _compose_approval_role_mapping_scope_value
   - 2988 _expand_approval_role_mapping_scope
   - 3014 _approval_role_mapping_scope_rank
   - 3025 _approval_role_mapping_scope_label
   - 3041 list_approval_role_mappings
   - 3095 upsert_approval_role_mapping
   - 3170 _approval_role_mapping_governance_review_history
   - 3224 _approval_role_mapping_governance_review_snapshot
   - 3249 control_approval_role_mapping_cleanup_review

2. Service registry / policy board reads
   service.py
   - 3363 get_approval_role_mapping_registry
   - 3505 export_approval_role_mapping_registry
   - 3582 get_approval_role_mapping_policy_board
   - 3805 export_approval_role_mapping_policy_board
   - 3905 get_approval_role_mapping_cleanup_board
   - 4155 export_approval_role_mapping_cleanup_board
   - 4248 get_approval_role_mapping_cleanup_policy_board
   - 4510 export_approval_role_mapping_cleanup_policy_board

3. Service cleanup apply / history / rollback
   service.py
   - 4596 _approval_role_mapping_cleanup_history_entries_from_properties
   - 4639 _approval_role_mapping_cleanup_change_log
   - 4675 _normalize_approval_role_mapping_cleanup_rollback_approval
   - 4715 _approval_role_mapping_cleanup_rollback_gate_summary
   - 4772 preview_approval_role_mapping_cleanup_policy
   - 4975 apply_approval_role_mapping_cleanup_policy
   - 5131 get_approval_role_mapping_cleanup_history
   - 5413 export_approval_role_mapping_cleanup_history
   - 5515 rollback_approval_role_mapping_cleanup_batch
   - 5652 _resolve_approval_role_mapping
   - 5726 _matching_approval_role_mappings

4. Router endpoints
   subcontracting_router.py
   - 9115 upsert endpoint
   - 9404 registry endpoints
   - 9481 policy board endpoints
   - 9558 cleanup board endpoints
   - 9631 cleanup policy board endpoints
   - 9718 cleanup apply preview endpoint
   - 9765 cleanup apply endpoint
   - 9807 cleanup history endpoints
   - 9880 cleanup rollback endpoint

5. Service tests
   test_subcontracting_service.py
   - 2091 registry
   - 2212 policy board
   - 2387 cleanup board
   - 2512 cleanup policy board
   - 2640 preview/apply
   - 2786 history/rollback

6. Router tests
   test_subcontracting_router.py
   - 9982 registry endpoints
   - 10084 policy board endpoints
   - 10151 cleanup board endpoints
   - 10214 cleanup policy board endpoints
   - 10279 cleanup apply preview/execute endpoints
   - 10375 cleanup history/rollback endpoints

Rule:
- use `git add -p`
- keep vendor-message / receipt / return hunks out of the first cut
EOF
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
- inspect hunk order with `--hunks`
- stage with `git add -p`, not `git add .`
- keep this incision isolated from vendor message / receipt / return flows
EOF
