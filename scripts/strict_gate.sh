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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="${PYTHONPATH:-src}"

PYTEST_BIN="${PYTEST_BIN:-${REPO_ROOT}/.venv/bin/pytest}"
PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD:-npx playwright test}"

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

if ! run_step "playwright" bash -lc "$PLAYWRIGHT_CMD"; then
  have_fail=1
fi

if [[ "$have_fail" -ne 0 ]]; then
  echo ""
  echo "STRICT_GATE: FAIL"
  exit 1
fi

echo ""
echo "STRICT_GATE: PASS"
