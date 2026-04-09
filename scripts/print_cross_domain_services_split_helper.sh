#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_cross_domain_services_split_helper.sh [--git-add-cmd] [--branch-plan]

Options:
  --git-add-cmd  Print the exact git add command for the cross-domain-services split.
  --branch-plan  Print the one-page execution note for the cross-domain-services split.
  -h, --help     Show help.

Default output:
  Prints the included code/docs/migrations families for the cross-domain-services split.
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
  "src/yuantus/meta_engine/approvals"
  "src/yuantus/meta_engine/document_sync"
  "src/yuantus/meta_engine/models/eco.py"
  "src/yuantus/meta_engine/models/parallel_tasks.py"
  "src/yuantus/meta_engine/services/eco_service.py"
  "src/yuantus/meta_engine/services/parallel_tasks_service.py"
  "src/yuantus/meta_engine/services/release_validation.py"
  "src/yuantus/meta_engine/web/approvals_router.py"
  "src/yuantus/meta_engine/web/change_router.py"
  "src/yuantus/meta_engine/web/document_sync_router.py"
  "src/yuantus/meta_engine/web/eco_router.py"
  "src/yuantus/meta_engine/web/file_router.py"
  "src/yuantus/meta_engine/web/parallel_tasks_router.py"
  "src/yuantus/meta_engine/web/query_router.py"
  "src/yuantus/meta_engine/web/store_router.py"
  "src/yuantus/meta_engine/web/version_router.py"
  "src/yuantus/meta_engine/bootstrap.py"
  "src/yuantus/meta_engine/tests/test_approvals_router.py"
  "src/yuantus/meta_engine/tests/test_approvals_service.py"
  "src/yuantus/meta_engine/tests/test_document_sync_router.py"
  "src/yuantus/meta_engine/tests/test_document_sync_service.py"
  "src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py"
  "src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py"
  "src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py"
  "src/yuantus/meta_engine/tests/test_file_viewer_readiness.py"
  "src/yuantus/meta_engine/tests/test_parallel_tasks_router.py"
  "src/yuantus/meta_engine/tests/test_parallel_tasks_services.py"
  "src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py"
  "src/yuantus/meta_engine/tests/test_bootstrap_domain_model_registration.py"
  "docs/DOCUMENT_SYNC_MIRROR_COMPATIBILITY_READING_GUIDE_20260407.md"
  "docs/DOC_SYNC_CHECKOUT_GOVERNANCE_ENHANCEMENT_READING_GUIDE_20260404.md"
  "docs/ECO_ACTIVITY_CHAIN_RELEASE_READINESS_LINKAGE_READING_GUIDE_20260406.md"
  "docs/ECO_BOM_COMPARE_MODE_INTEGRATION_READING_GUIDE_20260405.md"
  "docs/ECO_SUSPENSION_GATE_READING_GUIDE_20260406.md"
  "docs/WORKFLOW_CUSTOM_ACTION_PREDICATE_UPGRADE_READING_GUIDE_20260406.md"
  "migrations/versions/c4d5e6f7a8b9_add_breakage_incident_identity_dimensions.py"
  "migrations/versions/e6f7a8b9c0d1_add_document_sync_site_auth_contract.py"
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
Cross-domain-services branch execution note:

Suggested branch:
- feature/cross-domain-followups

Suggested commit title:
- feat(meta-engine): split cross-domain service followups

Step 1: inspect scope
- bash scripts/print_dirty_tree_domain_commands.sh --domain cross-domain-services --status
- bash scripts/print_dirty_tree_domain_commands.sh --domain cross-domain-services --commit-plan

Step 2: stage the domain
EOF
  print_git_add_cmd
  cat <<'EOF'

Step 3: review staged result
- git diff --cached --stat
- git diff --cached -- src/yuantus/meta_engine/approvals
- git diff --cached -- src/yuantus/meta_engine/document_sync
- git diff --cached -- src/yuantus/meta_engine/web
- git diff --cached -- migrations/versions

Rule:
- keep docs-parallel out
- keep subcontracting out
- keep strict-gate and delivery-pack out
- this split mixes code, docs, and migrations on purpose; do not widen it with unrelated domains
EOF
  exit 0
fi

cat <<'EOF'
Cross-domain-services split helper:

Includes:
- approvals
- document_sync
- ECO / parallel_tasks models and services
- related routers, tests, and bootstrap wiring
- owning reading guides and migrations

Excludes:
- subcontracting
- docs-parallel bulk
- strict-gate
- delivery-pack

Fast commands:
- bash scripts/print_cross_domain_services_split_helper.sh --git-add-cmd
- bash scripts/print_cross_domain_services_split_helper.sh --branch-plan
EOF
