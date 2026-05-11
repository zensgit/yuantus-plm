#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_cad_material_delivery_git_commands.sh [--git-add-cmd] [--review-cmds]

Options:
  --git-add-cmd  Print the exact git add command for the CAD Material Sync delivery package.
  --review-cmds  Print focused review and verification commands before commit.
  -h, --help     Show help.

Default output:
  Prints both the review commands and the precise git add command.
EOF
}

PRINT_GIT_ADD_CMD="false"
PRINT_REVIEW_CMDS="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --git-add-cmd)
      PRINT_GIT_ADD_CMD="true"
      shift
      ;;
    --review-cmds)
      PRINT_REVIEW_CMDS="true"
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

PATHS=(
  ".gitignore"
  "README.md"
  "clients/autocad-material-sync"
  "plugins/yuantus-cad-material-sync"
  "src/yuantus/web/workbench.html"
  "src/yuantus/api/tests/test_workbench_router.py"
  "src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py"
  "scripts/verify_cad_material_diff_confirm_contract.py"
  "scripts/verify_cad_material_delivery_package.py"
  "scripts/print_cad_material_delivery_git_commands.sh"
  "playwright/tests/cad_material_workbench_ui.spec.js"
  "docs/samples/cad_material_diff_confirm_fixture.json"
  "docs/CAD_MATERIAL_SYNC_GITHUB_HANDOFF_20260506.md"
  "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
  "docs/DEVELOPMENT_CLAUDE_TASK_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
  "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
)

DOC_GLOB="docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_*.md"

print_git_add_cmd() {
  printf 'git add --'
  for rel in "${PATHS[@]}"; do
    printf ' \\\n  %q' "${rel}"
  done
  printf ' \\\n  %s\n' "${DOC_GLOB}"
}

print_review_cmds() {
  cat <<'EOF'
python3 scripts/verify_cad_material_delivery_package.py
git diff --check -- \
  .gitignore \
  README.md \
  clients/autocad-material-sync \
  plugins/yuantus-cad-material-sync \
  scripts/verify_cad_material_diff_confirm_contract.py \
  scripts/verify_cad_material_delivery_package.py \
  scripts/print_cad_material_delivery_git_commands.sh \
  src/yuantus/web/workbench.html \
  src/yuantus/api/tests/test_workbench_router.py \
  src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py \
  playwright/tests/cad_material_workbench_ui.spec.js \
  docs/samples/cad_material_diff_confirm_fixture.json \
  docs/CAD_MATERIAL_SYNC_GITHUB_HANDOFF_20260506.md \
  docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md \
  docs/DEVELOPMENT_CLAUDE_TASK_CAD_MATERIAL_SYNC_PLUGIN_20260506.md \
  docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md \
  docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_*.md
git status --short -- \
  .gitignore \
  README.md \
  clients/autocad-material-sync \
  plugins/yuantus-cad-material-sync \
  scripts/verify_cad_material_diff_confirm_contract.py \
  scripts/verify_cad_material_delivery_package.py \
  scripts/print_cad_material_delivery_git_commands.sh \
  src/yuantus/web/workbench.html \
  src/yuantus/api/tests/test_workbench_router.py \
  src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py \
  playwright/tests/cad_material_workbench_ui.spec.js \
  docs/samples/cad_material_diff_confirm_fixture.json \
  docs/CAD_MATERIAL_SYNC_GITHUB_HANDOFF_20260506.md \
  docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md \
  docs/DEVELOPMENT_CLAUDE_TASK_CAD_MATERIAL_SYNC_PLUGIN_20260506.md \
  docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md \
  docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_*.md
EOF
}

if [[ "${PRINT_GIT_ADD_CMD}" == "true" && "${PRINT_REVIEW_CMDS}" == "true" ]]; then
  echo "ERROR: choose only one of --git-add-cmd or --review-cmds" >&2
  exit 2
fi

if [[ "${PRINT_GIT_ADD_CMD}" == "true" ]]; then
  print_git_add_cmd
  exit 0
fi

if [[ "${PRINT_REVIEW_CMDS}" == "true" ]]; then
  print_review_cmds
  exit 0
fi

cat <<'EOF'
CAD Material Sync delivery review commands:
EOF
print_review_cmds
cat <<'EOF'

CAD Material Sync precise staging command:
EOF
print_git_add_cmd
cat <<'EOF'

Do not include:
- .claude/
- local-dev-env/
- docs/DELIVERY_DOC_INDEX.md unless deliberately closing the delivery index separately
- AutoCAD build outputs under clients/autocad-material-sync/CADDedupPlugin/bin or obj
EOF
