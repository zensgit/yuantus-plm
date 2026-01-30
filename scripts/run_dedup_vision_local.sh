#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEDUP_VISION_ROOT="${DEDUP_VISION_ROOT:-}"
if [[ -z "$DEDUP_VISION_ROOT" ]]; then
  for candidate in "$ROOT_DIR/../dedupcad-vision" \
                  "/Users/huazhou/Downloads/Github/dedupcad-vision"; do
    if [[ -f "$candidate/start_server.py" ]]; then
      DEDUP_VISION_ROOT="$candidate"
      break
    fi
  done
fi

if [[ -z "$DEDUP_VISION_ROOT" ]]; then
  echo "Missing DEDUP_VISION_ROOT. Set DEDUP_VISION_ROOT=/path/to/dedupcad-vision" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Missing python3 (set PYTHON_BIN=...)" >&2
  exit 2
fi

DEDUP_VISION_HOST="${DEDUP_VISION_HOST:-127.0.0.1}"
DEDUP_VISION_PORT="${DEDUP_VISION_PORT:-8100}"
DEDUP_VISION_LOG="${DEDUP_VISION_LOG:-/tmp/dedup_vision_${DEDUP_VISION_PORT}.log}"
DEDUP_VISION_PIDFILE="${DEDUP_VISION_PIDFILE:-/tmp/dedup_vision_${DEDUP_VISION_PORT}.pid}"
NOHUP_BIN="${NOHUP_BIN:-/usr/bin/nohup}"

DEDUP_VISION_S3_ENABLED="${DEDUP_VISION_S3_ENABLED:-false}"
DEDUP_VISION_EVENT_BUS_ENABLED="${DEDUP_VISION_EVENT_BUS_ENABLED:-false}"
DEDUP_VISION_AUTH_MODE="${DEDUP_VISION_AUTH_MODE:-disabled}"

if [[ -f "$DEDUP_VISION_PIDFILE" ]]; then
  existing_pid="$(cat "$DEDUP_VISION_PIDFILE" 2>/dev/null || true)"
  if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" >/dev/null 2>&1; then
    echo "Dedup Vision already running (pid=$existing_pid)."
    echo "Base URL: http://${DEDUP_VISION_HOST}:${DEDUP_VISION_PORT}"
    exit 0
  fi
fi

cmd=(
  env
  S3_ENABLED="$DEDUP_VISION_S3_ENABLED"
  EVENT_BUS_ENABLED="$DEDUP_VISION_EVENT_BUS_ENABLED"
  INTEGRATION_AUTH_MODE="$DEDUP_VISION_AUTH_MODE"
  "$PYTHON_BIN" "$DEDUP_VISION_ROOT/start_server.py"
  --host "$DEDUP_VISION_HOST" --port "$DEDUP_VISION_PORT"
)

if command -v "$NOHUP_BIN" >/dev/null 2>&1; then
  "$NOHUP_BIN" "${cmd[@]}" >"$DEDUP_VISION_LOG" 2>&1 &
else
  "${cmd[@]}" >"$DEDUP_VISION_LOG" 2>&1 &
fi

vision_pid=$!
echo "$vision_pid" >"$DEDUP_VISION_PIDFILE"

echo "Starting Dedup Vision (pid=$vision_pid)..."
health_host="$DEDUP_VISION_HOST"
if [[ "$health_host" == "0.0.0.0" ]]; then
  health_host="127.0.0.1"
fi

for _ in {1..30}; do
  if curl -sSf "http://${health_host}:${DEDUP_VISION_PORT}/health" >/dev/null; then
    echo "Dedup Vision is healthy: http://${health_host}:${DEDUP_VISION_PORT}"
    echo "export YUANTUS_DEDUP_VISION_BASE_URL=\"http://${health_host}:${DEDUP_VISION_PORT}\""
    exit 0
  fi
  sleep 1
done

echo "Dedup Vision started, but health check failed. Log: $DEDUP_VISION_LOG" >&2
exit 1
