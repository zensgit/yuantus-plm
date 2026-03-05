#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_playwright_strict_gate.sh [--help]

Environment:
  PLAYWRIGHT_CMD=<cmd>            Optional. Default: npx playwright test --workers=1
  PLAYWRIGHT_MAX_ATTEMPTS=<n>     Optional. Default: 2
  PLAYWRIGHT_RETRYABLE_PATTERN=<re> Optional. Extended regex for retryable failures.
                                   Default matches bind/startup socket conflicts. Must be valid ERE.
  PLAYWRIGHT_PORT=<port>          Optional. If unset, auto-select a free localhost port.
  PLAYWRIGHT_BASE_URL=<url>       Optional. If unset, derived from PLAYWRIGHT_PORT.
  YUANTUS_PLAYWRIGHT_DB_PATH=<p>  Optional. If unset, generated per-attempt temp sqlite path.
  PLAYWRIGHT_KEEP_DB=1            Optional. If set, keeps sqlite db/shm/wal files after run.
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

PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD:-npx playwright test --workers=1}"
PLAYWRIGHT_MAX_ATTEMPTS="${PLAYWRIGHT_MAX_ATTEMPTS:-2}"
PLAYWRIGHT_RETRYABLE_PATTERN="${PLAYWRIGHT_RETRYABLE_PATTERN:-error while attempting to bind on address|address already in use|operation not permitted}"
PLAYWRIGHT_KEEP_DB="${PLAYWRIGHT_KEEP_DB:-0}"

if ! [[ "$PLAYWRIGHT_MAX_ATTEMPTS" =~ ^[0-9]+$ ]] || [[ "$PLAYWRIGHT_MAX_ATTEMPTS" -lt 1 ]]; then
  echo "ERROR: PLAYWRIGHT_MAX_ATTEMPTS must be a positive integer, got: ${PLAYWRIGHT_MAX_ATTEMPTS}" >&2
  exit 2
fi
if grep -Eq "$PLAYWRIGHT_RETRYABLE_PATTERN" <<<"" >/dev/null 2>&1; then
  :
else
  grep_rc=$?
  if [[ "$grep_rc" -eq 2 ]]; then
    echo "ERROR: PLAYWRIGHT_RETRYABLE_PATTERN is not a valid extended regex: ${PLAYWRIGHT_RETRYABLE_PATTERN}" >&2
    exit 2
  fi
fi

pick_playwright_port() {
  python3 - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
}

is_retryable_failure() {
  local log_path="$1"
  grep -Eqi "$PLAYWRIGHT_RETRYABLE_PATTERN" "$log_path" || return 1
}

cleanup_db_files() {
  local db_path="$1"
  if [[ "$PLAYWRIGHT_KEEP_DB" == "1" || "$PLAYWRIGHT_KEEP_DB" == "true" || "$PLAYWRIGHT_KEEP_DB" == "yes" ]]; then
    return 0
  fi
  rm -f "$db_path" "${db_path}-shm" "${db_path}-wal"
}

attempt=1
while [[ "$attempt" -le "$PLAYWRIGHT_MAX_ATTEMPTS" ]]; do
  port="${PLAYWRIGHT_PORT:-$(pick_playwright_port)}"
  base_url="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:${port}}"
  db_path="${YUANTUS_PLAYWRIGHT_DB_PATH:-/tmp/yuantus_playwright_${port}_$$.db}"

  echo "PLAYWRIGHT_ATTEMPT=${attempt}"
  echo "PLAYWRIGHT_PORT=${port}"
  echo "PLAYWRIGHT_BASE_URL=${base_url}"
  echo "PLAYWRIGHT_DB_PATH=${db_path}"
  echo "PLAYWRIGHT_MAX_ATTEMPTS=${PLAYWRIGHT_MAX_ATTEMPTS}"
  echo "PLAYWRIGHT_KEEP_DB=${PLAYWRIGHT_KEEP_DB}"
  echo "PLAYWRIGHT_RETRYABLE_PATTERN=${PLAYWRIGHT_RETRYABLE_PATTERN}"

  run_log="$(mktemp)"
  if env PORT="$port" BASE_URL="$base_url" YUANTUS_PLAYWRIGHT_DB_PATH="$db_path" bash -lc "$PLAYWRIGHT_CMD" >"$run_log" 2>&1; then
    cat "$run_log"
    cleanup_db_files "$db_path"
    rm -f "$run_log"
    exit 0
  else
    exit_code=$?
  fi

  cat "$run_log"
  cleanup_db_files "$db_path"
  if [[ "$attempt" -lt "$PLAYWRIGHT_MAX_ATTEMPTS" ]] && is_retryable_failure "$run_log"; then
    echo "Playwright retry: detected retryable bind/startup failure (attempt ${attempt}/${PLAYWRIGHT_MAX_ATTEMPTS})." >&2
    unset PLAYWRIGHT_PORT PLAYWRIGHT_BASE_URL YUANTUS_PLAYWRIGHT_DB_PATH
    rm -f "$run_log"
    attempt=$((attempt + 1))
    continue
  fi

  rm -f "$run_log"
  exit "$exit_code"
done
