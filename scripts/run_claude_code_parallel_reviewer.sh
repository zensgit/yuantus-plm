#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_claude_code_parallel_reviewer.sh [--repo PATH] [--branch NAME] [--out PATH] [--prompt TEXT]

Run Claude Code CLI in non-interactive reviewer mode for the current repo.

Examples:
  bash scripts/run_claude_code_parallel_reviewer.sh
  bash scripts/run_claude_code_parallel_reviewer.sh --out /tmp/yuantus-review.txt
  bash scripts/run_claude_code_parallel_reviewer.sh --prompt 'Read-only audit the current branch and list the top 3 residual risks.'
EOF
}

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"

REPO_PATH="${REPO_ROOT}"
BRANCH_NAME="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'main')"
OUT_PATH=""
PROMPT=""

while (($# > 0)); do
  case "$1" in
    --repo)
      REPO_PATH="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH_NAME="${2:-}"
      shift 2
      ;;
    --out)
      OUT_PATH="${2:-}"
      shift 2
      ;;
    --prompt)
      PROMPT="${2:-}"
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

if [[ -z "${PROMPT}" ]]; then
  PROMPT="In repo ${REPO_PATH} on branch ${BRANCH_NAME}, do a read-only audit. Do not edit files. Treat output as advisory only; do not authorize implementation, merge, phase transition, production cutover, or evidence signoff. Return only 3 bullets: top residual risk, shortest reviewer path, and next safest step."
fi

claude auth status >/dev/null

if [[ -n "${OUT_PATH}" ]]; then
  mkdir -p "$(dirname "${OUT_PATH}")"
  (
    cd "${REPO_PATH}"
    printf '%s\n' "${PROMPT}" | claude -p --no-session-persistence --tools ""
  ) | tee "${OUT_PATH}"
else
  (
    cd "${REPO_PATH}"
    printf '%s\n' "${PROMPT}" | claude -p --no-session-persistence --tools ""
  )
fi
