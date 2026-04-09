#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_docs_parallel_split_helper.sh [--git-add-cmd] [--branch-plan]

Options:
  --git-add-cmd  Print the exact git add command for the docs-parallel split.
  --branch-plan  Print the one-page execution note for the docs-parallel split.
  -h, --help     Show help.

Default output:
  Prints the included and excluded document families for the docs-parallel split.
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
  ":(glob)docs/DESIGN_PARALLEL_*"
  ":(glob)docs/DEV_AND_VERIFICATION_PARALLEL_*"
  ":(glob)docs/*READING_GUIDE_202604*.md"
  ":(glob)docs/PERFORMANCE_REPORTS/ROADMAP_9_3_*.md"
  ":(exclude,glob)docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_*"
  ":(exclude,glob)docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_*"
  ":(exclude,glob)docs/SUBCONTRACTING_*"
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
Docs-parallel branch execution note:

Suggested branch:
- docs/parallel-artifact-pack

Suggested commit title:
- docs(parallel): split verification artifact pack

Step 1: inspect scope
- bash scripts/print_dirty_tree_domain_commands.sh --domain docs-parallel --status
- bash scripts/print_dirty_tree_domain_commands.sh --domain docs-parallel --commit-plan

Step 2: stage the doc pack
EOF
  print_git_add_cmd
  cat <<'EOF'

Step 3: review staged result
- git diff --cached --stat
- git diff --cached -- docs

Rule:
- keep subcontracting-specific docs out
- do not mix cross-domain service code or migrations into this doc pack
- this split is bulk documentation staging; prefer exact pathspec staging over `git add .`
EOF
  exit 0
fi

cat <<'EOF'
Docs-parallel split helper:

Includes:
- docs/DESIGN_PARALLEL_*
- docs/DEV_AND_VERIFICATION_PARALLEL_*
- docs/*READING_GUIDE_202604*.md
- docs/PERFORMANCE_REPORTS/ROADMAP_9_3_*.md

Excludes:
- docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_*
- docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_*
- docs/SUBCONTRACTING_*

Fast commands:
- bash scripts/print_docs_parallel_split_helper.sh --git-add-cmd
- bash scripts/print_docs_parallel_split_helper.sh --branch-plan
EOF
