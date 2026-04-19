#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: print_mainline_baseline_switch_commands.sh [--repo PATH] [--base-branch REF] [--worktree-name NAME] [--worktree-branch NAME] [--backup-branch NAME]

Print safe command templates for preserving a dirty feature worktree and
switching to a clean mainline baseline worktree.

Examples:
  bash scripts/print_mainline_baseline_switch_commands.sh
  bash scripts/print_mainline_baseline_switch_commands.sh --base-branch origin/main --worktree-name mainline-20260414
EOF
}

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"

REPO_PATH="${REPO_ROOT}"
BASE_BRANCH="origin/main"
CURRENT_BRANCH="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || printf 'main')"
STAMP="$(date '+%Y%m%d-%H%M%S')"
WORKTREE_NAME="mainline-${STAMP}"
WORKTREE_BRANCH="baseline/${WORKTREE_NAME}"
WORKTREE_BRANCH_EXPLICIT="0"
BACKUP_BRANCH="backup/${CURRENT_BRANCH//\//-}-${STAMP}"

while (($# > 0)); do
  case "$1" in
    --repo)
      REPO_PATH="${2:-}"
      shift 2
      ;;
    --base-branch)
      BASE_BRANCH="${2:-}"
      shift 2
      ;;
    --worktree-name)
      WORKTREE_NAME="${2:-}"
      shift 2
      ;;
    --backup-branch)
      BACKUP_BRANCH="${2:-}"
      shift 2
      ;;
    --worktree-branch)
      WORKTREE_BRANCH="${2:-}"
      WORKTREE_BRANCH_EXPLICIT="1"
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

if [[ "${WORKTREE_BRANCH_EXPLICIT}" != "1" ]]; then
  WORKTREE_BRANCH="baseline/${WORKTREE_NAME}"
fi

WORKTREE_PARENT="$(dirname "${REPO_PATH}")/$(basename "${REPO_PATH}")-worktrees"
WORKTREE_PATH="${WORKTREE_PARENT}/${WORKTREE_NAME}"

repo_q="$(printf '%q' "${REPO_PATH}")"
base_q="$(printf '%q' "${BASE_BRANCH}")"
backup_q="$(printf '%q' "${BACKUP_BRANCH}")"
worktree_parent_q="$(printf '%q' "${WORKTREE_PARENT}")"
worktree_path_q="$(printf '%q' "${WORKTREE_PATH}")"
worktree_branch_q="$(printf '%q' "${WORKTREE_BRANCH}")"

cat <<EOF
# Mainline baseline switch templates
# repo: ${REPO_PATH}
# current branch: ${CURRENT_BRANCH}
# baseline ref: ${BASE_BRANCH}
# suggested backup branch: ${BACKUP_BRANCH}
# suggested worktree: ${WORKTREE_PATH}
# suggested worktree branch: ${WORKTREE_BRANCH}

## 1) Inspect current state
git -C ${repo_q} status --short
git -C ${repo_q} rev-list --left-right --count ${CURRENT_BRANCH}...${base_q}

## 2) Preserve the dirty worktree before any branch surgery
git -C ${repo_q} branch ${backup_q} HEAD
git -C ${repo_q} diff --binary > /tmp/$(basename "${REPO_PATH}")-${STAMP}.patch
git -C ${repo_q} diff --cached --binary > /tmp/$(basename "${REPO_PATH}")-${STAMP}-staged.patch
git -C ${repo_q} stash push -u -m 'baseline-switch ${STAMP}'

## 3) Create a clean mainline worktree
mkdir -p ${worktree_parent_q}
git -C ${repo_q} worktree add -b ${worktree_branch_q} ${worktree_path_q} ${base_q}

## 4) Re-apply only the current-branch unique commits if still wanted
git -C ${worktree_path_q} cherry-pick f9076f4 09b30e2 e42c79e d24b5a4 6738eac a50f400

## 5) Optional: run Claude Code in the clean worktree
claude auth status
claude --worktree ${WORKTREE_NAME} --add-dir ${repo_q} 'Work only in the clean ${BASE_BRANCH} baseline worktree. Re-apply the minimal current-branch deltas, keep the scope narrow, and inspect git status first.'

## 6) Rollback / recovery references
git -C ${repo_q} stash list --max-count=5
git -C ${repo_q} branch --list ${backup_q}

EOF
