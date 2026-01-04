#!/usr/bin/env bash
# =============================================================================
# CADGF preview public-base verification (local).
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CADGF_ROOT="${CADGF_ROOT:-/Users/huazhou/Downloads/Github/CADGameFusion}"
ROUTER_PORT="${ROUTER_PORT:-9100}"
YUANTUS_PORT="${YUANTUS_PORT:-8100}"
PY="${PY:-.venv/bin/python}"
UVICORN="${UVICORN:-.venv/bin/uvicorn}"
CURL="${CURL:-curl -sS}"

if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 || true)"
fi
if [[ -z "$PY" ]]; then
  echo "Missing python3 (set PY=...)" >&2
  exit 2
fi
if [[ ! -x "$UVICORN" ]]; then
  if command -v uvicorn >/dev/null 2>&1; then
    UVICORN="$(command -v uvicorn)"
  else
    echo "Missing uvicorn (set UVICORN=...)" >&2
    exit 2
  fi
fi
if [[ ! -f "$CADGF_ROOT/tools/plm_router_service.py" ]]; then
  echo "Missing CADGameFusion root at $CADGF_ROOT (set CADGF_ROOT=...)" >&2
  exit 2
fi

CADGF_PLUGIN_PATH="${CADGF_PLUGIN_PATH:-$CADGF_ROOT/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib}"
CADGF_CONVERT_CLI="${CADGF_CONVERT_CLI:-$CADGF_ROOT/build_vcpkg/tools/convert_cli}"
SAMPLE_FILE="${SAMPLE_FILE:-$CADGF_ROOT/tests/plugin_data/importer_sample.json}"

if [[ ! -f "$CADGF_PLUGIN_PATH" ]]; then
  echo "Missing CADGF plugin at $CADGF_PLUGIN_PATH (set CADGF_PLUGIN_PATH=...)" >&2
  exit 2
fi
if [[ ! -x "$CADGF_CONVERT_CLI" ]]; then
  echo "Missing CADGF convert_cli at $CADGF_CONVERT_CLI (set CADGF_CONVERT_CLI=...)" >&2
  exit 2
fi
if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "Missing sample file at $SAMPLE_FILE (set SAMPLE_FILE=...)" >&2
  exit 2
fi

export YUANTUS_DATABASE_URL="sqlite:////tmp/yuantus_cadgf_public_base.db"
export YUANTUS_LOCAL_STORAGE_PATH="/tmp/yuantus_cadgf_public_base_storage"
export YUANTUS_CADGF_ROUTER_BASE_URL="http://127.0.0.1:${ROUTER_PORT}"
export YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL="http://127.0.0.1:${ROUTER_PORT}/cadgf"

python3 "$CADGF_ROOT/tools/plm_router_service.py" \
  --host 127.0.0.1 --port "$ROUTER_PORT" \
  --default-plugin "$CADGF_PLUGIN_PATH" \
  --default-convert-cli "$CADGF_CONVERT_CLI" \
  >/tmp/cadgf_router_public_base.log 2>&1 &
ROUTER_PID=$!

PYTHONPATH="$ROOT_DIR/src" "$UVICORN" yuantus.api.app:app \
  --host 127.0.0.1 --port "$YUANTUS_PORT" \
  >/tmp/yuantus_api_public_base.log 2>&1 &
YUANTUS_PID=$!

cleanup() {
  kill "$ROUTER_PID" "$YUANTUS_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in {1..40}; do
  $CURL "http://127.0.0.1:${ROUTER_PORT}/health" | grep -q '"ok"' && break
  sleep 1
done
for _ in {1..40}; do
  $CURL "http://127.0.0.1:${YUANTUS_PORT}/api/v1/health" | grep -q '"ok"' && break
  sleep 1
done

$CURL "http://127.0.0.1:${YUANTUS_PORT}/api/v1/cad-preview" \
  | grep -Fq "routerBaseUrl: \\\"http://127.0.0.1:${ROUTER_PORT}/cadgf\\\""

RESP=$($CURL -X POST "http://127.0.0.1:${YUANTUS_PORT}/api/v1/cad-preview/convert" \
  -F "file=@$SAMPLE_FILE" \
  -F "emit=json,gltf,meta" \
  -F "project_id=demo" \
  -F "document_label=sample")

STATUS=$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("status",""))' <<<"$RESP")
if [[ "$STATUS" != "ok" ]]; then
  echo "$RESP" >&2
  exit 1
fi

VIEWER_URL=$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("viewer_url", ""))' <<<"$RESP")
case "$VIEWER_URL" in
  http://127.0.0.1:${ROUTER_PORT}/cadgf/*) ;;
  *) echo "viewer_url_mismatch:$VIEWER_URL" >&2; exit 1 ;;
esac

REAL_VIEWER_URL=${VIEWER_URL/\/cadgf/}
$CURL "$REAL_VIEWER_URL" | grep -q "Web Preview"

echo "public_base_smoke_ok"
