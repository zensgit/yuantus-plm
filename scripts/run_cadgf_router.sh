#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CADGF_ROOT="${CADGF_ROOT:-}"
if [[ -z "$CADGF_ROOT" ]]; then
  for candidate in "${CADGF_HOST_ROOT:-}" "$ROOT_DIR/CADGameFusion" "/Users/huazhou/Downloads/Github/CADGameFusion"; do
    if [[ -n "$candidate" && -f "$candidate/tools/plm_router_service.py" ]]; then
      CADGF_ROOT="$candidate"
      break
    fi
  done
fi

if [[ -z "$CADGF_ROOT" ]]; then
  echo "Missing CADGF_ROOT. Set CADGF_ROOT=/path/to/CADGameFusion" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-${CADGF_PYTHON_BIN:-python3}}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Missing python3 (set PYTHON_BIN=...)" >&2
  exit 2
fi

CADGF_PLUGIN_PATH="${CADGF_PLUGIN_PATH:-$CADGF_ROOT/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib}"
if [[ ! -f "$CADGF_PLUGIN_PATH" ]]; then
  alt_plugin="$CADGF_ROOT/build_vcpkg/plugins/libcadgf_json_importer_plugin.so"
  if [[ -f "$alt_plugin" ]]; then
    CADGF_PLUGIN_PATH="$alt_plugin"
  else
    echo "Missing CADGF plugin at $CADGF_PLUGIN_PATH (set CADGF_PLUGIN_PATH=...)" >&2
    exit 2
  fi
fi

CADGF_CONVERT_CLI="${CADGF_CONVERT_CLI:-$CADGF_ROOT/build_vcpkg/tools/convert_cli}"
if [[ ! -x "$CADGF_CONVERT_CLI" ]]; then
  echo "Missing CADGF convert_cli at $CADGF_CONVERT_CLI (set CADGF_CONVERT_CLI=...)" >&2
  exit 2
fi

CADGF_ROUTER_HOST="${CADGF_ROUTER_HOST:-127.0.0.1}"
CADGF_ROUTER_PORT="${CADGF_ROUTER_PORT:-9000}"
CADGF_ROUTER_LOG="${CADGF_ROUTER_LOG:-/tmp/cadgf_router_${CADGF_ROUTER_PORT}.log}"
CADGF_ROUTER_PIDFILE="${CADGF_ROUTER_PIDFILE:-/tmp/cadgf_router_${CADGF_ROUTER_PORT}.pid}"
NOHUP_BIN="${NOHUP_BIN:-/usr/bin/nohup}"

if [[ -f "$CADGF_ROUTER_PIDFILE" ]]; then
  existing_pid="$(cat "$CADGF_ROUTER_PIDFILE" 2>/dev/null || true)"
  if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" >/dev/null 2>&1; then
    echo "CADGF router already running (pid=$existing_pid)."
    echo "Base URL: http://${CADGF_ROUTER_HOST}:${CADGF_ROUTER_PORT}"
    exit 0
  fi
fi

if command -v "$NOHUP_BIN" >/dev/null 2>&1; then
  "$NOHUP_BIN" "$PYTHON_BIN" -u "$CADGF_ROOT/tools/plm_router_service.py" \
    --host "$CADGF_ROUTER_HOST" --port "$CADGF_ROUTER_PORT" \
    --default-plugin "$CADGF_PLUGIN_PATH" \
    --default-convert-cli "$CADGF_CONVERT_CLI" \
    >"$CADGF_ROUTER_LOG" 2>&1 &
else
  "$PYTHON_BIN" -u "$CADGF_ROOT/tools/plm_router_service.py" \
    --host "$CADGF_ROUTER_HOST" --port "$CADGF_ROUTER_PORT" \
    --default-plugin "$CADGF_PLUGIN_PATH" \
    --default-convert-cli "$CADGF_CONVERT_CLI" \
    >"$CADGF_ROUTER_LOG" 2>&1 &
fi

router_pid=$!
echo "$router_pid" >"$CADGF_ROUTER_PIDFILE"

echo "Starting CADGF router (pid=$router_pid)..."
health_host="$CADGF_ROUTER_HOST"
if [[ "$health_host" == "0.0.0.0" ]]; then
  health_host="127.0.0.1"
fi

for _ in {1..30}; do
  if curl -sS "http://${health_host}:${CADGF_ROUTER_PORT}/health" | grep -q '"ok"'; then
    echo "CADGF router is healthy: http://${health_host}:${CADGF_ROUTER_PORT}"
    echo "export YUANTUS_CADGF_ROUTER_BASE_URL=\"http://${health_host}:${CADGF_ROUTER_PORT}\""
    exit 0
  fi
  sleep 1
done

echo "CADGF router started, but health check failed. Log: $CADGF_ROUTER_LOG" >&2
exit 1
