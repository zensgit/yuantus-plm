#!/usr/bin/env bash
# Strict gate runner:
# - optional targeted pytest (set TARGETED_PYTEST_ARGS)
# - pytest (non-DB)
# - pytest (DB opt-in via YUANTUS_PYTEST_DB=1)
# - Playwright e2e
#
# This script is intentionally CI-friendly (single exit code) and does not write
# repo-tracked files. Use `scripts/strict_gate_report.sh` for a markdown report.
set -uo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/strict_gate.sh [--help]

Environment:
  TARGETED_PYTEST_ARGS=<arg> Optional. If set, runs an extra targeted pytest step.
  PYTEST_BIN=<path>          Optional. Default: .venv/bin/pytest

  PLAYWRIGHT_RUNNER=<path>   Optional. Default: scripts/run_playwright_strict_gate.sh
  PLAYWRIGHT_CMD=<cmd>       Optional. Default: npx playwright test --workers=1
  PLAYWRIGHT_RETRYABLE_PATTERN=<re> Optional. Passed through to playwright runner.
  PLAYWRIGHT_PORT=<port>     Optional. Passed through to playwright runner.
  PLAYWRIGHT_BASE_URL=<url>  Optional. Passed through to playwright runner.
  PLAYWRIGHT_DB_PATH=<path>  Optional. Passed through as YUANTUS_PLAYWRIGHT_DB_PATH.
  PLAYWRIGHT_MAX_ATTEMPTS=<n> Optional. Default: 2
  PLAYWRIGHT_KEEP_DB=1       Optional. If set, keeps playwright sqlite files.
EOF
}

if [[ $# -ge 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
  usage
  exit 0
fi
if [[ $# -ne 0 ]]; then
  echo "ERROR: unexpected arguments: $*" >&2
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="${PYTHONPATH:-src}"

PYTEST_BIN="${PYTEST_BIN:-${REPO_ROOT}/.venv/bin/pytest}"
PLAYWRIGHT_RUNNER="${PLAYWRIGHT_RUNNER:-${REPO_ROOT}/scripts/run_playwright_strict_gate.sh}"
PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD:-npx playwright test --workers=1}"
PLAYWRIGHT_RETRYABLE_PATTERN="${PLAYWRIGHT_RETRYABLE_PATTERN:-}"
PLAYWRIGHT_PORT="${PLAYWRIGHT_PORT:-}"
PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-}"
PLAYWRIGHT_DB_PATH="${PLAYWRIGHT_DB_PATH:-}"
PLAYWRIGHT_MAX_ATTEMPTS="${PLAYWRIGHT_MAX_ATTEMPTS:-2}"
PLAYWRIGHT_KEEP_DB="${PLAYWRIGHT_KEEP_DB:-0}"

if ! [[ "$PLAYWRIGHT_MAX_ATTEMPTS" =~ ^[0-9]+$ ]] || [[ "$PLAYWRIGHT_MAX_ATTEMPTS" -lt 1 ]]; then
  echo "ERROR: PLAYWRIGHT_MAX_ATTEMPTS must be a positive integer, got: ${PLAYWRIGHT_MAX_ATTEMPTS}" >&2
  exit 2
fi
if [[ -n "$PLAYWRIGHT_RETRYABLE_PATTERN" ]]; then
  grep -Eq "$PLAYWRIGHT_RETRYABLE_PATTERN" <<<"" >/dev/null 2>&1
  grep_rc=$?
  if [[ "$grep_rc" -eq 2 ]]; then
    echo "ERROR: PLAYWRIGHT_RETRYABLE_PATTERN is not a valid extended regex: ${PLAYWRIGHT_RETRYABLE_PATTERN}" >&2
    exit 2
  fi
fi

have_fail=0

run_step() {
  local name="$1"
  shift
  echo ""
  echo "==> ${name}"
  "$@"
}

if [[ ! -x "$PYTEST_BIN" ]]; then
  echo "ERROR: pytest not found at $PYTEST_BIN" >&2
  exit 2
fi
if [[ ! -x "$PLAYWRIGHT_RUNNER" ]]; then
  echo "ERROR: playwright runner not found or not executable at $PLAYWRIGHT_RUNNER" >&2
  exit 2
fi

if [[ -n "${TARGETED_PYTEST_ARGS:-}" ]]; then
  if ! run_step "pytest (targeted)" "$PYTEST_BIN" -q ${TARGETED_PYTEST_ARGS}; then
    have_fail=1
  fi
else
  echo "==> pytest (targeted): SKIP (TARGETED_PYTEST_ARGS not set)"
fi

if ! run_step "pytest (non-DB)" "$PYTEST_BIN" -q; then
  have_fail=1
fi

if ! run_step "pytest (DB)" env YUANTUS_PYTEST_DB=1 "$PYTEST_BIN" -q; then
  have_fail=1
fi

if ! run_step "playwright" env \
  PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD" \
  PLAYWRIGHT_RETRYABLE_PATTERN="$PLAYWRIGHT_RETRYABLE_PATTERN" \
  PLAYWRIGHT_PORT="$PLAYWRIGHT_PORT" \
  PLAYWRIGHT_BASE_URL="$PLAYWRIGHT_BASE_URL" \
  YUANTUS_PLAYWRIGHT_DB_PATH="$PLAYWRIGHT_DB_PATH" \
  PLAYWRIGHT_MAX_ATTEMPTS="$PLAYWRIGHT_MAX_ATTEMPTS" \
  PLAYWRIGHT_KEEP_DB="$PLAYWRIGHT_KEEP_DB" \
  "$PLAYWRIGHT_RUNNER"; then
  have_fail=1
fi

if [[ "$have_fail" -ne 0 ]]; then
  echo ""
  echo "STRICT_GATE: FAIL"
  exit 1
fi

echo ""
echo "STRICT_GATE: PASS"
