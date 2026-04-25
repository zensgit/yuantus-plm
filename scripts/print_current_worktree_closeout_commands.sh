#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_current_worktree_closeout_commands.sh [--commands] [--group NAME]

Options:
  --commands    Print ready-to-copy review and staging command templates.
  --group NAME  Print only one group. Supported:
                closeout-docs-and-index
                closeout-tooling
                odoo18-verifier-hardening
                router-decomposition-portfolio
  -h, --help    Show help.

Default output:
  Prints the current worktree closeout split plan for the active router
  decomposition and Odoo18 verifier hardening batch.
EOF
}

PRINT_COMMANDS="false"
GROUP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --commands)
      PRINT_COMMANDS="true"
      shift
      ;;
    --group)
      GROUP="${2:-}"
      shift 2
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

validate_group() {
  case "$1" in
    ""|closeout-docs-and-index|closeout-tooling|odoo18-verifier-hardening|router-decomposition-portfolio)
      return 0
      ;;
    *)
      echo "ERROR: unsupported group: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
}

print_plan_group() {
  case "$1" in
    closeout-docs-and-index)
      cat <<'EOF'
1. closeout-docs-and-index
   intent: delivery docs, closeout records, and local-only index guard
   validation: doc index contracts + git diff --check
EOF
      ;;
    closeout-tooling)
      cat <<'EOF'
2. closeout-tooling
   intent: helper script, its contract test, CI wiring, and scripts index verification
   validation: helper contract + shell syntax + CI wiring/order + scripts index contracts
EOF
      ;;
    odoo18-verifier-hardening)
      cat <<'EOF'
3. odoo18-verifier-hardening
   intent: Odoo18 PLM stack verifier script, workflow, and focused contracts
   validation: verifier focused contracts + smoke/full stack verifier
EOF
      ;;
    router-decomposition-portfolio)
      cat <<'EOF'
4. router-decomposition-portfolio
   intent: split-router modules, app registration, router tests, and router closeout docs
   validation: family-specific router contracts before merge
EOF
      ;;
  esac
}

print_command_group() {
  case "$1" in
    closeout-docs-and-index)
      cat <<'EOF'
1. closeout-docs-and-index
  git diff --stat -- docs/DELIVERY_DOC_INDEX.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_20260425.md docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_VERIFIER_HARDENING_CLOSEOUT_20260425.md docs/DEV_AND_VERIFICATION_LOCAL_ONLY_ARTIFACT_INDEX_GUARD_20260425.md src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
  git add -- docs/DELIVERY_DOC_INDEX.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_20260425.md docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_VERIFIER_HARDENING_CLOSEOUT_20260425.md docs/DEV_AND_VERIFICATION_LOCAL_ONLY_ARTIFACT_INDEX_GUARD_20260425.md src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
EOF
      ;;
    closeout-tooling)
      cat <<'EOF'
2. closeout-tooling
   git diff --stat -- scripts/print_current_worktree_closeout_commands.sh docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/meta_engine/tests/test_ci_contracts_current_worktree_closeout_commands.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_PR_SPLIT_COMMANDS_20260425.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_ROUTER_STAGING_SCOPE_GUARD_20260425.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_TOOLING_GROUP_20260425.md .github/workflows/ci.yml
   git add -- scripts/print_current_worktree_closeout_commands.sh docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/meta_engine/tests/test_ci_contracts_current_worktree_closeout_commands.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_PR_SPLIT_COMMANDS_20260425.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_ROUTER_STAGING_SCOPE_GUARD_20260425.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_TOOLING_GROUP_20260425.md .github/workflows/ci.yml
EOF
      ;;
    odoo18-verifier-hardening)
      cat <<'EOF'
3. odoo18-verifier-hardening
   git diff --stat -- scripts/verify_odoo18_plm_stack.sh .github/workflows/odoo18-plm-stack-regression.yml .github/workflows/ci.yml docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_runtime.py
   git add -- scripts/verify_odoo18_plm_stack.sh .github/workflows/odoo18-plm-stack-regression.yml .github/workflows/ci.yml docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_runtime.py
EOF
      ;;
    router-decomposition-portfolio)
      cat <<'EOF'
4. router-decomposition-portfolio
   git diff --stat -- src/yuantus/api/app.py ':(glob)src/yuantus/meta_engine/web/approval*_router.py' ':(glob)src/yuantus/meta_engine/web/box*_router.py' ':(glob)src/yuantus/meta_engine/web/cutted_parts*_router.py' ':(glob)src/yuantus/meta_engine/web/document_sync*_router.py' ':(glob)src/yuantus/meta_engine/web/maintenance*_router.py' ':(glob)src/yuantus/meta_engine/web/quality*_router.py' src/yuantus/meta_engine/web/quality_common.py ':(glob)src/yuantus/meta_engine/web/report*_router.py' ':(glob)src/yuantus/meta_engine/web/subcontracting*_router.py' ':(glob)src/yuantus/meta_engine/web/version*_router.py' ':(glob)src/yuantus/meta_engine/tests/test_approval*_router*.py' src/yuantus/meta_engine/tests/test_approvals_router.py ':(glob)src/yuantus/meta_engine/tests/test_box_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_cutted_parts_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_document_sync*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_maintenance*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_quality*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_report*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_subcontracting*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_version*_router*.py' src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py ':(glob)docs/DEV_AND_VERIFICATION_*ROUTER_DECOMPOSITION*' docs/DEVELOPMENT_CLAUDE_TASK_REPORT_ROUTER_DECOMPOSITION_20260424.md
   git add -- src/yuantus/api/app.py ':(glob)src/yuantus/meta_engine/web/approval*_router.py' ':(glob)src/yuantus/meta_engine/web/box*_router.py' ':(glob)src/yuantus/meta_engine/web/cutted_parts*_router.py' ':(glob)src/yuantus/meta_engine/web/document_sync*_router.py' ':(glob)src/yuantus/meta_engine/web/maintenance*_router.py' ':(glob)src/yuantus/meta_engine/web/quality*_router.py' src/yuantus/meta_engine/web/quality_common.py ':(glob)src/yuantus/meta_engine/web/report*_router.py' ':(glob)src/yuantus/meta_engine/web/subcontracting*_router.py' ':(glob)src/yuantus/meta_engine/web/version*_router.py' ':(glob)src/yuantus/meta_engine/tests/test_approval*_router*.py' src/yuantus/meta_engine/tests/test_approvals_router.py ':(glob)src/yuantus/meta_engine/tests/test_box_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_cutted_parts_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_document_sync*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_maintenance*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_quality*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_report*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_subcontracting*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_version*_router*.py' src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py ':(glob)docs/DEV_AND_VERIFICATION_*ROUTER_DECOMPOSITION*' docs/DEVELOPMENT_CLAUDE_TASK_REPORT_ROUTER_DECOMPOSITION_20260424.md
EOF
      ;;
  esac
}

print_local_only_exclusions() {
  cat <<'EOF'
Local-only exclusions:
   .claude/
   local-dev-env/
EOF
}

validate_group "${GROUP}"

CLOSEOUT_GROUPS=(
  "closeout-docs-and-index"
  "closeout-tooling"
  "odoo18-verifier-hardening"
  "router-decomposition-portfolio"
)

if [[ "${PRINT_COMMANDS}" == "true" ]]; then
  if [[ -n "${GROUP}" ]]; then
    print_command_group "${GROUP}"
  else
    for group in "${CLOSEOUT_GROUPS[@]}"; do
      print_command_group "${group}"
      echo
    done
  fi
  cat <<'EOF'
Never stage local-only artifacts:
   .claude/
   local-dev-env/
EOF
  exit 0
fi

echo "Current worktree closeout split plan:"
echo
if [[ -n "${GROUP}" ]]; then
  print_plan_group "${GROUP}"
else
  for group in "${CLOSEOUT_GROUPS[@]}"; do
    print_plan_group "${group}"
    echo
  done
fi

echo
print_local_only_exclusions

cat <<'EOF'

Print command templates with:
   bash scripts/print_current_worktree_closeout_commands.sh --commands
EOF

if [[ -n "${GROUP}" ]]; then
  echo "   bash scripts/print_current_worktree_closeout_commands.sh --group ${GROUP} --commands"
else
  echo "   bash scripts/print_current_worktree_closeout_commands.sh --group closeout-docs-and-index --commands"
fi
