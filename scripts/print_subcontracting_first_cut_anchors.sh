#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_subcontracting_first_cut_anchors.sh [--grep] [--hunks] [--checklist] [--decisions] [--branch-plan]

Options:
  --grep     Print ready-to-run grep commands for the first subcontracting cut.
  --hunks    Print the recommended git-add-p hunk order for the first cut.
  --checklist
             Print a per-file git-add-p operator checklist for the first cut.
  --decisions
             Print a y/n/s/defer cheat sheet for git-add-p decisions.
  --branch-plan
             Print the one-page branch execution note for the first cut.
  -h, --help Show help.

Default output:
  Prints the likely files and anchor tokens for the approval role mapping
  cleanup cluster inside the subcontracting domain.
EOF
}

PRINT_GREP="false"
PRINT_HUNKS="false"
PRINT_CHECKLIST="false"
PRINT_DECISIONS="false"
PRINT_BRANCH_PLAN="false"

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
    --checklist)
      PRINT_CHECKLIST="true"
      shift
      ;;
    --decisions)
      PRINT_DECISIONS="true"
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
for flag in "${PRINT_GREP}" "${PRINT_HUNKS}" "${PRINT_CHECKLIST}" "${PRINT_DECISIONS}" "${PRINT_BRANCH_PLAN}"; do
  if [[ "${flag}" == "true" ]]; then
    selected_count=$((selected_count + 1))
  fi
done

if [[ "${selected_count}" -gt 1 ]]; then
  echo "ERROR: choose only one of --grep, --hunks, --checklist, --decisions, or --branch-plan" >&2
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

if [[ "${PRINT_CHECKLIST}" == "true" ]]; then
  cat <<'EOF'
Per-file git add -p operator checklist for the first subcontracting cut:

Anchor tokens to accept:
- approval_role_mapping
- cleanup_policy
- cleanup_history
- role_mapping_registry
- role_mapping_policy_board
- role_mapping_cleanup_board

service.py
- accept first:
  - scope helpers + CRUD seed
  - registry / policy board reads
  - cleanup apply / history / rollback helpers
- skip for now:
  - vendor-message / receipt / return flows
  - unrelated supplier settlement or transport hunks
  - broad import churn unless required by accepted approval-role-mapping hunks

subcontracting_router.py
- accept first:
  - approval role mapping upsert endpoint
  - registry / policy board endpoints
  - cleanup board / cleanup policy board endpoints
  - cleanup preview / apply / history / rollback endpoints
- skip for now:
  - unrelated vendor receipt / return / messaging endpoints
  - router-wide refactors not required by approval-role-mapping routes

test_subcontracting_service.py
- accept first:
  - registry tests
  - policy board tests
  - cleanup board + cleanup policy board tests
  - preview / apply tests
  - history / rollback tests
- skip for now:
  - unrelated subcontract receipt / return fixtures
  - fixture rewrites that are not needed for approval-role-mapping coverage

test_subcontracting_router.py
- accept first:
  - registry endpoint tests
  - policy board endpoint tests
  - cleanup board / cleanup policy board endpoint tests
  - cleanup preview / execute endpoint tests
  - cleanup history / rollback endpoint tests
- skip for now:
  - unrelated route matrix expansions
  - auth / fixture churn that is not required by approval-role-mapping routes

Rule:
- stage file by file with `git add -p`
- if a hunk mixes approval-role-mapping code with vendor receipt / return code, split it
- if a hunk cannot be split cleanly, leave it out of the first cut

Operator workflow:
- git add -p src/yuantus/meta_engine/subcontracting/service.py
- git add -p src/yuantus/meta_engine/web/subcontracting_router.py
- git add -p src/yuantus/meta_engine/tests/test_subcontracting_service.py
- git add -p src/yuantus/meta_engine/tests/test_subcontracting_router.py
EOF
  exit 0
fi

if [[ "${PRINT_DECISIONS}" == "true" ]]; then
  cat <<'EOF'
git add -p decision cheat sheet for the first subcontracting cut:

accept with y
- hunk contains approval-role-mapping anchor tokens:
  - approval_role_mapping
  - cleanup_policy
  - cleanup_history
  - role_mapping_registry
  - role_mapping_policy_board
  - role_mapping_cleanup_board
- hunk is inside the first-cut service / router / test ranges already listed by `--hunks`
- hunk is a direct test or endpoint companion for approval-role-mapping cleanup

reject with n
- hunk touches vendor-message flow
- hunk touches receipt flow
- hunk touches return flow
- hunk is unrelated supplier settlement / transport logic
- hunk is broad import churn or formatting-only noise with no first-cut anchors

split with s
- hunk mixes approval-role-mapping code with vendor-message / receipt / return code
- hunk mixes first-cut endpoints with unrelated router handlers
- hunk mixes first-cut tests with unrelated route matrix expansions
- hunk mixes anchor-token lines with large fixture churn

defer
- hunk cannot be split cleanly in `git add -p`
- hunk depends on a later subcontracting slice outside the first cut
- hunk is a migration or doc follow-up you cannot confidently tie to the accepted code hunks
- hunk likely causes cross-domain spillover into docs-parallel or cross-domain-services
EOF
  exit 0
fi

if [[ "${PRINT_BRANCH_PLAN}" == "true" ]]; then
  cat <<'EOF'
First-cut branch execution note:

Suggested branch:
- feature/subcontracting-split

Step 1: inspect scope
- bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --status
- bash scripts/print_dirty_tree_domain_commands.sh --domain subcontracting --commit-plan
- bash scripts/print_subcontracting_first_cut_anchors.sh --grep

Step 2: inspect staging guidance
- bash scripts/print_subcontracting_first_cut_anchors.sh --hunks
- bash scripts/print_subcontracting_first_cut_anchors.sh --checklist
- bash scripts/print_subcontracting_first_cut_anchors.sh --decisions

Step 3: stage only the first cut
- git add -p src/yuantus/meta_engine/subcontracting/service.py
- git add -p src/yuantus/meta_engine/web/subcontracting_router.py
- git add -p src/yuantus/meta_engine/tests/test_subcontracting_service.py
- git add -p src/yuantus/meta_engine/tests/test_subcontracting_router.py

Step 4: review staged result
- git diff --cached --stat
- git diff --cached -- src/yuantus/meta_engine/subcontracting/service.py
- git diff --cached -- src/yuantus/meta_engine/web/subcontracting_router.py
- git diff --cached -- src/yuantus/meta_engine/tests/test_subcontracting_service.py
- git diff --cached -- src/yuantus/meta_engine/tests/test_subcontracting_router.py

Step 5: minimum local checks
- ./.venv/bin/python -m pytest src/yuantus/meta_engine/tests/test_ci_contracts_subcontracting_first_cut_anchors.py -q
- ./.venv/bin/python -m pytest src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py -q

Suggested commit title:
- feat(subcontracting): split approval role mapping cleanup cluster

Rule:
- do not use `git add .`
- if a hunk mixes approval-role-mapping code with vendor-message / receipt / return code, split or defer it
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
- inspect per-file checklist with `--checklist`
- inspect y/n/s/defer guide with `--decisions`
- inspect final execution note with `--branch-plan`
- stage with `git add -p`, not `git add .`
- keep this incision isolated from vendor message / receipt / return flows
EOF
