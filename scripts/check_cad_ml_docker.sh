#!/usr/bin/env bash
# =============================================================================
# Quick health check for cad-ml-platform (Docker)
# =============================================================================
set -euo pipefail

CAD_ML_API_PORT="${CAD_ML_API_PORT:-18000}"
CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-http://127.0.0.1:${CAD_ML_API_PORT}}"
CAD_ML_HEALTH_URL="${CAD_ML_HEALTH_URL:-${CAD_ML_BASE_URL}/api/v1/health}"

TMP="$(mktemp -t cadml_health_XXXXXX)"
cleanup() {
  rm -f "$TMP"
}
trap cleanup EXIT

HTTP_CODE="$(curl -sS -o "$TMP" -w '%{http_code}' "$CAD_ML_HEALTH_URL" || true)"
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "cad-ml health check failed (HTTP ${HTTP_CODE})" >&2
  head -c 400 "$TMP" >&2 || true
  echo >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  CADML_JSON="$(cat "$TMP")" python3 - <<'PY'
import json
import os
data = json.loads(os.environ.get("CADML_JSON") or "{}")
status = data.get("status")
services = data.get("services") or {}
runtime = data.get("runtime") or {}
print("cad-ml health: ok")
print(f"  status: {status}")
print(f"  services: {services}")
print(f"  metrics_enabled: {runtime.get('metrics_enabled')}")
PY
else
  echo "cad-ml health: ok"
  head -c 400 "$TMP" || true
  echo
fi
