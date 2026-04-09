#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_strict_gate_split_helper.sh [--git-add-cmd] [--branch-plan]

Options:
  --git-add-cmd  Print the exact git add command for the strict-gate split.
  --branch-plan  Print the one-page execution note for the strict-gate split.
  -h, --help     Show help.

Default output:
  Prints the included scripts and contract/runtime tests for the strict-gate split.
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
  "scripts/run_playwright_strict_gate.sh"
  "scripts/strict_gate.sh"
  "scripts/strict_gate_report.sh"
  "src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_playwright_runner.py"
  "src/yuantus/meta_engine/tests/test_strict_gate_report_runtime_notes_contracts.py"
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
Strict-gate branch execution note:

Suggested branch:
- chore/strict-gate-followups

Suggested commit title:
- chore(strict-gate): split runner and contract updates

Step 1: inspect scope
- bash scripts/print_dirty_tree_domain_commands.sh --domain strict-gate --status
- bash scripts/print_dirty_tree_domain_commands.sh --domain strict-gate --commit-plan

Step 2: stage the strict-gate slice
EOF
  print_git_add_cmd
  cat <<'EOF'

Step 3: review staged result
- git diff --cached --stat
- git diff --cached -- scripts/run_playwright_strict_gate.sh
- git diff --cached -- scripts/strict_gate.sh
- git diff --cached -- scripts/strict_gate_report.sh

Rule:
- keep delivery-pack out
- keep cross-domain-services out
- keep docs-parallel out
- this split is ops/runtime focused; do not widen it with unrelated feature code
EOF
  exit 0
fi

cat <<'EOF'
Strict-gate split helper:

Includes:
- run_playwright_strict_gate.sh
- strict_gate.sh
- strict_gate_report.sh
- strict-gate runtime / contract tests

Excludes:
- delivery-pack
- docs-parallel
- cross-domain-services
- subcontracting

Fast commands:
- bash scripts/print_strict_gate_split_helper.sh --git-add-cmd
- bash scripts/print_strict_gate_split_helper.sh --branch-plan
EOF
