#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_dirty_tree_domain_commands.sh [--list-domains]
  scripts/print_dirty_tree_domain_commands.sh [--recommended-order]
  scripts/print_dirty_tree_domain_commands.sh --domain NAME [--status | --git-add-cmd | --commit-plan]

Options:
  --list-domains  List supported dirty-tree domains and their intent.
  --recommended-order
                 Print the suggested dirty-tree split order with short reasons.
  --domain NAME   Target domain. Supported:
                  subcontracting
                  docs-parallel
                  cross-domain-services
                  strict-gate
                  migrations
                  delivery-pack
  --status        Show `git status --short` for the selected domain.
  --git-add-cmd   Print an exact `git add -- ...` command for the selected domain.
  --commit-plan   Print a suggested branch/commit skeleton plus the exact
                  staging command for the selected domain.
  -h, --help      Show help.

Default output:
  Prints the repo-relative pathspec list for the selected domain.
EOF
}

DOMAIN=""
LIST_DOMAINS="false"
PRINT_RECOMMENDED_ORDER="false"
SHOW_STATUS="false"
PRINT_GIT_ADD_CMD="false"
PRINT_COMMIT_PLAN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list-domains)
      LIST_DOMAINS="true"
      shift
      ;;
    --recommended-order)
      PRINT_RECOMMENDED_ORDER="true"
      shift
      ;;
    --domain)
      DOMAIN="${2:-}"
      shift 2
      ;;
    --status)
      SHOW_STATUS="true"
      shift
      ;;
    --git-add-cmd)
      PRINT_GIT_ADD_CMD="true"
      shift
      ;;
    --commit-plan)
      PRINT_COMMIT_PLAN="true"
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

if [[ "${LIST_DOMAINS}" == "true" && -n "${DOMAIN}" ]]; then
  echo "ERROR: --list-domains cannot be combined with --domain" >&2
  exit 2
fi

if [[ "${PRINT_RECOMMENDED_ORDER}" == "true" && -n "${DOMAIN}" ]]; then
  echo "ERROR: --recommended-order cannot be combined with --domain" >&2
  exit 2
fi

ops_selected=0
[[ "${SHOW_STATUS}" == "true" ]] && ((ops_selected+=1))
[[ "${PRINT_GIT_ADD_CMD}" == "true" ]] && ((ops_selected+=1))
[[ "${PRINT_COMMIT_PLAN}" == "true" ]] && ((ops_selected+=1))
if (( ops_selected > 1 )); then
  echo "ERROR: choose only one of --status, --git-add-cmd, or --commit-plan" >&2
  exit 2
fi

describe_domain() {
  case "$1" in
    subcontracting)
      echo "Largest accidental-scope domain: subcontracting source, router, tests, and dedicated docs."
      ;;
    docs-parallel)
      echo "Large parallel design / dev-verification document pack, excluding the main subcontracting code paths."
      ;;
    cross-domain-services)
      echo "Approvals, ECO, document-sync, file, and parallel-task service/router/test spillover."
      ;;
    strict-gate)
      echo "Strict-gate shell runner changes and related runtime contract test."
      ;;
    migrations)
      echo "Dirty Alembic migrations that should travel with their owning domain."
      ;;
    delivery-pack)
      echo "Delivery / handoff / manifest docs plus CONTRIBUTING.md."
      ;;
    *)
      return 1
      ;;
  esac
}

populate_domain_paths() {
  case "$1" in
    subcontracting)
      PATHS=(
        "src/yuantus/meta_engine/subcontracting"
        "src/yuantus/meta_engine/web/subcontracting_router.py"
        "src/yuantus/meta_engine/web/subcontracting_consumer_row_discoverability.py"
        "src/yuantus/meta_engine/web/subcontracting_governance_discoverability.py"
        "src/yuantus/meta_engine/web/subcontracting_governance_row_discoverability.py"
        "src/yuantus/meta_engine/tests/test_subcontracting_router.py"
        "src/yuantus/meta_engine/tests/test_subcontracting_service.py"
        "src/yuantus/meta_engine/tests/test_subcontracting_entry_contract.py"
        "src/yuantus/meta_engine/tests/test_subcontracting_consumer_row_discoverability.py"
        "src/yuantus/meta_engine/tests/test_subcontracting_governance_discoverability.py"
        "src/yuantus/meta_engine/tests/subcontracting_entry_contract_fixtures.py"
        "src/yuantus/meta_engine/tests/subcontracting_consumer_row_discoverability_fixtures.py"
        "src/yuantus/meta_engine/tests/subcontracting_governance_discoverability_fixtures.py"
        "migrations/versions/a2b2c3d4e7a6_add_approvals_and_subcontracting_tables.py"
        "migrations/versions/b3c4d5e6f7a8_add_subcontract_approval_role_mappings.py"
        ":(glob)docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_*"
        ":(glob)docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_*"
        ":(glob)docs/SUBCONTRACTING_*"
        ":(glob)docs/APPROVAL_ROLE_MAPPING_CLEANUP_CONTRACT_SURPASS_READING_GUIDE_20260401.md"
        ":(glob)docs/CONSUMER_NON_ROLLBACK_CONTRACT_SURPASS_READING_GUIDE_20260401.md"
        ":(glob)docs/CONSUMER_ROLLBACK_CONTRACT_SURPASS_READING_GUIDE_20260401.md"
        ":(glob)docs/RETURN_DISPOSITION_APPROVAL_CONTRACT_SURPASS_READING_GUIDE_20260401.md"
        ":(glob)docs/VENDOR_COLLABORATION_PACKET_CONTRACT_SURPASS_READING_GUIDE_20260401.md"
      )
      ;;
    docs-parallel)
      PATHS=(
        ":(glob)docs/DESIGN_PARALLEL_*"
        ":(glob)docs/DEV_AND_VERIFICATION_PARALLEL_*"
        ":(glob)docs/*READING_GUIDE_202604*.md"
        ":(glob)docs/PERFORMANCE_REPORTS/ROADMAP_9_3_*.md"
        ":(exclude,glob)docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_*"
        ":(exclude,glob)docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_*"
        ":(exclude,glob)docs/SUBCONTRACTING_*"
      )
      ;;
    cross-domain-services)
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
      ;;
    strict-gate)
      PATHS=(
        "scripts/run_playwright_strict_gate.sh"
        "scripts/strict_gate.sh"
        "scripts/strict_gate_report.sh"
        "src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_playwright_runner.py"
        "src/yuantus/meta_engine/tests/test_strict_gate_report_runtime_notes_contracts.py"
      )
      ;;
    migrations)
      PATHS=(
        "migrations/versions/a2b2c3d4e7a6_add_approvals_and_subcontracting_tables.py"
        "migrations/versions/b3c4d5e6f7a8_add_subcontract_approval_role_mappings.py"
        "migrations/versions/c4d5e6f7a8b9_add_breakage_incident_identity_dimensions.py"
        "migrations/versions/e6f7a8b9c0d1_add_document_sync_site_auth_contract.py"
      )
      ;;
    delivery-pack)
      PATHS=(
        "CONTRIBUTING.md"
        "docs/DELIVERY_DOC_INDEX.md"
        "docs/DELIVERY_EXTERNAL_HANDOFF_GUIDE_20260203.md"
        "docs/DELIVERY_EXTERNAL_VERIFY_COMMANDS_20260203.md"
        "docs/DELIVERY_PACKAGE_HASHES_20260203.md"
        "docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt"
        "docs/DELIVERY_PACKAGE_NOTE_20260203.md"
      )
      ;;
    *)
      echo "ERROR: unsupported domain: $1" >&2
      exit 2
      ;;
  esac
}

suggest_branch() {
  case "$1" in
    subcontracting) echo "feature/subcontracting-split" ;;
    docs-parallel) echo "docs/parallel-artifact-pack" ;;
    cross-domain-services) echo "feature/cross-domain-followups" ;;
    strict-gate) echo "chore/strict-gate-followups" ;;
    migrations) echo "feature/domain-migrations-followup" ;;
    delivery-pack) echo "docs/delivery-pack-followup" ;;
    *) echo "feature/dirty-tree-split" ;;
  esac
}

suggest_commit_title() {
  case "$1" in
    subcontracting) echo "feat(subcontracting): split large dirty-tree domain" ;;
    docs-parallel) echo "docs(parallel): split verification artifact pack" ;;
    cross-domain-services) echo "feat(meta-engine): split cross-domain service followups" ;;
    strict-gate) echo "chore(strict-gate): split runner and contract updates" ;;
    migrations) echo "db: split dirty-tree migration set" ;;
    delivery-pack) echo "docs(delivery): split handoff package updates" ;;
    *) echo "chore: split dirty-tree domain" ;;
  esac
}

print_recommended_order() {
  cat <<'EOF'
1. subcontracting
   Largest risk domain by both lines changed and feature blast radius.
2. docs-parallel
   Huge parallel doc bulk; remove reviewer noise early after the main code spike.
3. cross-domain-services
   Remaining approvals / ECO / document-sync / parallel-task spillover.
4. migrations
   Keep migrations with their owning domain; do not land them as a mixed tail.
5. strict-gate
   Small CI/operator follow-up domain that can be reviewed independently.
6. delivery-pack
   Lowest code risk; handoff/package docs should be finalized last.
EOF
}

if [[ "${PRINT_RECOMMENDED_ORDER}" == "true" ]]; then
  print_recommended_order
  exit 0
fi

if [[ "${LIST_DOMAINS}" == "true" || -z "${DOMAIN}" ]]; then
  for name in subcontracting docs-parallel cross-domain-services strict-gate migrations delivery-pack; do
    printf '%-24s %s\n' "${name}" "$(describe_domain "${name}")"
  done
  exit 0
fi

populate_domain_paths "${DOMAIN}"

if [[ "${SHOW_STATUS}" == "true" ]]; then
  git status --short -- "${PATHS[@]}"
  exit 0
fi

if [[ "${PRINT_GIT_ADD_CMD}" == "true" ]]; then
  printf 'git add --'
  for rel in "${PATHS[@]}"; do
    printf ' \\\n  %q' "${rel}"
  done
  printf '\n'
  exit 0
fi

if [[ "${PRINT_COMMIT_PLAN}" == "true" ]]; then
  cat <<EOF
Suggested branch:
  $(suggest_branch "${DOMAIN}")

Suggested commit title:
  $(suggest_commit_title "${DOMAIN}")

Suggested staging command:
EOF
  printf 'git add --'
  for rel in "${PATHS[@]}"; do
    printf ' \\\n  %q' "${rel}"
  done
  printf '\n'
  exit 0
fi

printf '%s\n' "${PATHS[@]}"
