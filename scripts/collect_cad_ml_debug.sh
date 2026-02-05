#!/usr/bin/env bash
# =============================================================================
# CAD-ML debug bundle collector
# =============================================================================
set -u

BASE_URL="${1:-${YUANTUS_BASE_URL:-http://127.0.0.1:7910}}"
CAD_ML_API_PORT="${CAD_ML_API_PORT:-18000}"
CAD_ML_API_METRICS_PORT="${CAD_ML_API_METRICS_PORT:-19090}"
CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-${YUANTUS_CAD_ML_BASE_URL:-http://127.0.0.1:${CAD_ML_API_PORT}}}"
CAD_ML_HEALTH_URL="${CAD_ML_HEALTH_URL:-${CAD_ML_BASE_URL}/api/v1/health}"
CAD_ML_VISION_HEALTH_URL="${CAD_ML_VISION_HEALTH_URL:-${CAD_ML_BASE_URL}/api/v1/vision/health}"
CAD_ML_METRICS_URL="${CAD_ML_METRICS_URL:-http://127.0.0.1:${CAD_ML_API_METRICS_PORT}/metrics}"
CAD_ML_DOCKER_CONTAINERS="${CAD_ML_DOCKER_CONTAINERS:-cad-ml-api cad-ml-redis}"
CURL="${CURL:-curl -sS}"

TS="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="/tmp/cad_ml_debug_${TS}"
mkdir -p "$OUT_DIR"

safe_bool() {
  local val="${1:-}"
  if [[ -n "$val" ]]; then
    echo "set"
  else
    echo "unset"
  fi
}

{
  echo "timestamp=$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  echo "base_url=$BASE_URL"
  echo "cad_ml_base_url=$CAD_ML_BASE_URL"
  echo "cad_ml_health_url=$CAD_ML_HEALTH_URL"
  echo "cad_ml_vision_health_url=$CAD_ML_VISION_HEALTH_URL"
  echo "cad_ml_metrics_url=$CAD_ML_METRICS_URL"
  echo "cad_ml_api_port=$CAD_ML_API_PORT"
  echo "cad_ml_api_metrics_port=$CAD_ML_API_METRICS_PORT"
  echo "cad_ml_docker_containers=$CAD_ML_DOCKER_CONTAINERS"
  echo "RUN_CAD_ML_DOCKER=${RUN_CAD_ML_DOCKER:-0}"
  echo "RUN_CAD_ML_METRICS=${RUN_CAD_ML_METRICS:-0}"
  echo "CAD_PREVIEW_SAMPLE_FILE=${CAD_PREVIEW_SAMPLE_FILE:-}"
  echo "YUANTUS_CAD_ML_BASE_URL=${YUANTUS_CAD_ML_BASE_URL:-}"
  echo "YUANTUS_CAD_ML_SERVICE_TOKEN=$(safe_bool "${YUANTUS_CAD_ML_SERVICE_TOKEN:-}")"
} > "${OUT_DIR}/env.txt"

{
  echo "uname:"
  uname -a || true
  echo ""
  echo "date:"
  date || true
} > "${OUT_DIR}/system.txt"

curl_with_code() {
  local url="$1"
  local out="$2"
  local code
  code="$($CURL -o "$out" -w '%{http_code}' "$url" 2>"${out}.err" || true)"
  echo "$code" > "${out}.code"
}

curl_with_code "$CAD_ML_HEALTH_URL" "${OUT_DIR}/cad_ml_health.json"
curl_with_code "$CAD_ML_VISION_HEALTH_URL" "${OUT_DIR}/cad_ml_vision_health.json"
curl_with_code "$CAD_ML_METRICS_URL" "${OUT_DIR}/cad_ml_metrics.txt"
curl_with_code "${BASE_URL}/api/v1/health" "${OUT_DIR}/yuantus_health.json"

if command -v docker >/dev/null 2>&1; then
  {
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
  } > "${OUT_DIR}/docker_ps.txt" 2>&1

  for c in $CAD_ML_DOCKER_CONTAINERS; do
    docker inspect -f '{{json .State}}' "$c" > "${OUT_DIR}/${c}_state.json" 2>&1 || true
    docker logs --tail=200 "$c" > "${OUT_DIR}/${c}.log" 2>&1 || true
  done
else
  echo "docker not available" > "${OUT_DIR}/docker_ps.txt"
fi

echo "cad-ml debug bundle captured: $OUT_DIR"
