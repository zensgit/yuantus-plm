#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/list_native_workspace_bundle.sh [--full] [--status] [--git-add-cmd] [--commit-plan]

Options:
  --full      Include tracked harness/docs entrypoints in addition to the core
              native workspace bundle files.
  --status    Show `git status --short` for the native workspace bundle files.
  --git-add-cmd
              Print an exact `git add -- ...` command for the selected scope.
  --commit-plan
              Print a suggested commit title/body skeleton plus the exact
              `git add -- ...` command for the selected scope.
  -h, --help  Show help.

Default output:
  Prints the repo-relative file list that defines the native PLM workspace
  bundle scope for staged/commit review.
EOF
}

SHOW_STATUS="false"
FULL_SCOPE="false"
PRINT_GIT_ADD_CMD="false"
PRINT_COMMIT_PLAN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full)
      FULL_SCOPE="true"
      shift
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FILES=(
  "src/yuantus/api/routers/favicon.py"
  "src/yuantus/api/routers/plm_workspace.py"
  "src/yuantus/api/routers/workbench.py"
  "src/yuantus/web/plm_workspace.html"
  "src/yuantus/web/workbench.html"
  "src/yuantus/api/tests/test_plm_workspace_router.py"
  "src/yuantus/api/tests/test_workbench_router.py"
  "playwright/tests/README_plm_workspace.md"
  "playwright/tests/helpers/plmWorkspaceDemo.js"
  "playwright/tests/plm_workspace_documents_ui.spec.js"
  "playwright/tests/plm_workspace_demo_resume.spec.js"
  "playwright/tests/plm_workspace_document_handoff.spec.js"
  "playwright/tests/plm_workspace_eco_actions.spec.js"
  "scripts/list_native_workspace_bundle.sh"
  "scripts/verify_playwright_plm_workspace_all.sh"
  "scripts/verify_playwright_plm_workspace_documents_ui.sh"
  "scripts/verify_playwright_plm_workspace_demo_resume.sh"
  "scripts/verify_playwright_plm_workspace_document_handoff.sh"
  "scripts/verify_playwright_plm_workspace_eco_actions.sh"
  "src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_bundle_scope.py"
  "src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_playwright_aggregate_wrapper.py"
  "src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_playwright_entrypoints.py"
  "src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_scope_script.py"
  "src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_ui_playwright_workspace_smokes.py"
  "src/yuantus/meta_engine/tests/test_delivery_scripts_index_native_workspace_playwright_contracts.py"
)

cd "$REPO_ROOT"

if [[ "$FULL_SCOPE" == "true" ]]; then
  FILES+=(
    "README.md"
    "docs/VERIFICATION.md"
    "docs/DELIVERY_SCRIPTS_INDEX_20260202.md"
    "package.json"
    "scripts/verify_all.sh"
    "src/yuantus/api/app.py"
    "src/yuantus/api/middleware/auth_enforce.py"
    "src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py"
  )
fi

if [[ "$SHOW_STATUS" == "true" && ( "$PRINT_GIT_ADD_CMD" == "true" || "$PRINT_COMMIT_PLAN" == "true" ) ]]; then
  echo "ERROR: --status cannot be combined with --git-add-cmd or --commit-plan" >&2
  exit 2
fi

if [[ "$SHOW_STATUS" == "true" ]]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required for --status" >&2
    exit 1
  fi
  git status --short -- "${FILES[@]}"
  exit 0
fi

if [[ "$PRINT_GIT_ADD_CMD" == "true" ]]; then
  printf 'git add --'
  for rel in "${FILES[@]}"; do
    printf ' \\\n  %q' "$rel"
  done
  printf '\n'
  exit 0
fi

if [[ "$PRINT_COMMIT_PLAN" == "true" ]]; then
  cat <<'EOF'
Suggested commit title:
  feat(plm-workspace): land native workspace browser harness bundle

Suggested commit body:
  - land native plm workspace shell, router test, and browser regressions
  - wire aggregate/native workspace playwright verification entrypoints
  - document bundle scope and commit/staging helpers for clean workspace rollout

Suggested staging command:
EOF
  printf 'git add --'
  for rel in "${FILES[@]}"; do
    printf ' \\\n  %q' "$rel"
  done
  printf '\n'
  exit 0
fi

printf '%s\n' "${FILES[@]}"
