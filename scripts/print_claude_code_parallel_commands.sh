#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: print_claude_code_parallel_commands.sh [--mode MODE] [--worktree-name NAME] [--repo PATH] [--branch NAME]

Print safe Claude Code CLI command templates for parallel development.

Modes:
  all        Print all templates (default)
  read-only  Read-only audit / summary in the current repo
  worktree   Isolated implementation in a git worktree
  reviewer   Reviewer / PR brief generation

Examples:
  bash scripts/print_claude_code_parallel_commands.sh
  bash scripts/print_claude_code_parallel_commands.sh --mode worktree --worktree-name claude-native-followup
  bash scripts/print_claude_code_parallel_commands.sh --mode reviewer
EOF
}

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"

MODE="all"
REPO_PATH="${REPO_ROOT}"
BRANCH_NAME="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'main')"
WORKTREE_NAME="claude-$(date '+%m%d-%H%M')"

while (($# > 0)); do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --worktree-name)
      WORKTREE_NAME="${2:-}"
      shift 2
      ;;
    --repo)
      REPO_PATH="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH_NAME="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "${MODE}" in
  all|read-only|worktree|reviewer)
    ;;
  *)
    printf 'Unsupported mode: %s\n\n' "${MODE}" >&2
    usage >&2
    exit 1
    ;;
esac

WORKTREE_PARENT="$(dirname "${REPO_PATH}")/$(basename "${REPO_PATH}")-worktrees"
WORKTREE_PATH="${WORKTREE_PARENT}/${WORKTREE_NAME}"

repo_q="$(printf '%q' "${REPO_PATH}")"
worktree_parent_q="$(printf '%q' "${WORKTREE_PARENT}")"
worktree_path_q="$(printf '%q' "${WORKTREE_PATH}")"

print_header() {
  cat <<EOF
# Claude Code parallel templates
# repo: ${REPO_PATH}
# branch: ${BRANCH_NAME}

claude auth status

EOF
}

print_read_only() {
  cat <<EOF
## read-only
(
  cd ${repo_q}
  printf '%s\n' 'In repo ${REPO_PATH} on branch ${BRANCH_NAME}, do a read-only audit. Do not edit files. Treat output as advisory only; do not authorize implementation, merge, phase transition, production cutover, or evidence signoff. Summarize current risks, remaining cleanup, and the shortest reviewer path.' | claude -p --no-session-persistence --tools ""
)

EOF
}

print_worktree() {
  cat <<EOF
## worktree
# Requires explicit user authorization before running.
mkdir -p ${worktree_parent_q}
claude --worktree ${WORKTREE_NAME} --add-dir ${repo_q} 'Work in an isolated git worktree for repo ${REPO_PATH} on branch ${BRANCH_NAME}. This write-mode run has explicit user authorization. Stay within one narrow scope, inspect git status first, keep the change set small and reviewable, do not use permission-skipping modes, and do not commit .claude/ or local-dev-env/.'
# expected worktree path: ${WORKTREE_PATH}

EOF
}

print_reviewer() {
  cat <<EOF
## reviewer
(
  cd ${repo_q}
  printf '%s\n' 'In repo ${REPO_PATH} on branch ${BRANCH_NAME}, write a concise reviewer brief: scope, changed files, verification commands, and residual risk. Do not edit files. Treat output as advisory only.' | claude -p --no-session-persistence --tools ""
)

EOF
}

print_header

case "${MODE}" in
  all)
    print_read_only
    print_worktree
    print_reviewer
    ;;
  read-only)
    print_read_only
    ;;
  worktree)
    print_worktree
    ;;
  reviewer)
    print_reviewer
    ;;
esac
