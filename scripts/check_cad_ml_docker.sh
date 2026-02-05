#!/usr/bin/env bash
# =============================================================================
# Quick health check for cad-ml-platform (Docker)
# =============================================================================
set -euo pipefail

CAD_ML_API_PORT="${CAD_ML_API_PORT:-18000}"
CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-http://127.0.0.1:${CAD_ML_API_PORT}}"
CAD_ML_HEALTH_URL="${CAD_ML_HEALTH_URL:-${CAD_ML_BASE_URL}/api/v1/health}"
CAD_ML_VISION_HEALTH_URL="${CAD_ML_VISION_HEALTH_URL:-${CAD_ML_BASE_URL}/api/v1/vision/health}"
CAD_ML_HEALTH_RETRIES="${CAD_ML_HEALTH_RETRIES:-10}"
CAD_ML_HEALTH_SLEEP_SECONDS="${CAD_ML_HEALTH_SLEEP_SECONDS:-2}"
CAD_ML_VISION_HEALTH_REQUIRED="${CAD_ML_VISION_HEALTH_REQUIRED:-1}"
CAD_ML_DOCKER_CONTAINERS="${CAD_ML_DOCKER_CONTAINERS:-cad-ml-api cad-ml-redis}"

TMP="$(mktemp -t cadml_health_XXXXXX)"
TMP_VISION="$(mktemp -t cadml_vision_health_XXXXXX)"
cleanup() {
  rm -f "$TMP"
  rm -f "$TMP_VISION"
}
trap cleanup EXIT

dump_docker_logs() {
  if ! command -v docker >/dev/null 2>&1; then
    return 0
  fi
  local ts
  ts="$(date +%Y%m%d-%H%M%S)"
  local out="/tmp/cad_ml_docker_logs_${ts}.log"
  {
    echo "timestamp=$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "containers=$CAD_ML_DOCKER_CONTAINERS"
    echo ""
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
    echo ""
    for c in $CAD_ML_DOCKER_CONTAINERS; do
      echo "==> docker logs $c (tail=200)"
      docker logs --tail=200 "$c" 2>&1 || echo "WARN: failed to read logs for $c"
      echo ""
    done
  } > "$out" 2>&1 || true
  echo "cad-ml docker logs captured: $out" >&2
}

probe_url() {
  local url="$1"
  local out_file="$2"
  local code="000"
  for i in $(seq 1 "$CAD_ML_HEALTH_RETRIES"); do
    code="$(curl -sS -o "$out_file" -w '%{http_code}' "$url" || true)"
    if [[ "$code" == "200" ]]; then
      break
    fi
    if [[ "$i" -lt "$CAD_ML_HEALTH_RETRIES" ]]; then
      sleep "$CAD_ML_HEALTH_SLEEP_SECONDS"
    fi
  done
  echo "$code"
}

HTTP_CODE="$(probe_url "$CAD_ML_HEALTH_URL" "$TMP")"
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "cad-ml health check failed (HTTP ${HTTP_CODE})" >&2
  head -c 400 "$TMP" >&2 || true
  echo >&2
  dump_docker_logs
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

VISION_CODE="$(probe_url "$CAD_ML_VISION_HEALTH_URL" "$TMP_VISION")"
if [[ "$VISION_CODE" != "200" ]]; then
  if [[ "$CAD_ML_VISION_HEALTH_REQUIRED" == "1" ]]; then
    echo "cad-ml vision health check failed (HTTP ${VISION_CODE})" >&2
    head -c 400 "$TMP_VISION" >&2 || true
    echo >&2
    dump_docker_logs
    exit 1
  else
    echo "WARN: cad-ml vision health unavailable (HTTP ${VISION_CODE})" >&2
    head -c 400 "$TMP_VISION" >&2 || true
    echo >&2
  fi
else
  if command -v python3 >/dev/null 2>&1; then
    CADML_VISION_JSON="$(cat "$TMP_VISION")" python3 - <<'PY'
import json
import os
raw = os.environ.get("CADML_VISION_JSON") or "{}"
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    data = {}
print("cad-ml vision health: ok")
status = data.get("status")
if status is not None:
    print(f"  status: {status}")
PY
  else
    echo "cad-ml vision health: ok"
    head -c 400 "$TMP_VISION" || true
    echo
  fi
fi
