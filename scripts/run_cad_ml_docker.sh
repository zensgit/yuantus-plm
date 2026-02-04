#!/usr/bin/env bash
# =============================================================================
# One-click start for cad-ml-platform (Docker compose)
# =============================================================================
set -euo pipefail

CAD_ML_REPO="${CAD_ML_REPO:-/Users/huazhou/Downloads/Github/cad-ml-platform}"
CAD_ML_COMPOSE_FILE="${CAD_ML_COMPOSE_FILE:-deployments/docker/docker-compose.yml}"
CAD_ML_API_PORT="${CAD_ML_API_PORT:-18000}"
CAD_ML_API_METRICS_PORT="${CAD_ML_API_METRICS_PORT:-19090}"
CAD_ML_REDIS_PORT="${CAD_ML_REDIS_PORT:-16379}"
CAD_ML_BUILD="${CAD_ML_BUILD:-0}"
CAD_ML_FORCE_RECREATE="${CAD_ML_FORCE_RECREATE:-0}"
CAD_ML_SERVICES="${CAD_ML_SERVICES:-cad-ml-api redis}"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

if [[ ! -d "$CAD_ML_REPO" ]]; then
  fail "cad-ml-platform repo not found at $CAD_ML_REPO (set CAD_ML_REPO=...)"
fi

COMPOSE_PATH="${CAD_ML_REPO}/${CAD_ML_COMPOSE_FILE}"
if [[ ! -f "$COMPOSE_PATH" ]]; then
  fail "Compose file not found: $COMPOSE_PATH (set CAD_ML_COMPOSE_FILE=...)"
fi

compose_cmd=(docker compose -f "$COMPOSE_PATH")

if [[ "$CAD_ML_BUILD" == "1" ]]; then
  "${compose_cmd[@]}" build cad-ml-api
fi

extra_flags=()
if [[ "$CAD_ML_FORCE_RECREATE" == "1" ]]; then
  extra_flags+=(--force-recreate)
fi

CAD_ML_API_PORT="$CAD_ML_API_PORT" \
CAD_ML_API_METRICS_PORT="$CAD_ML_API_METRICS_PORT" \
CAD_ML_REDIS_PORT="$CAD_ML_REDIS_PORT" \
  "${compose_cmd[@]}" up -d --no-build "${extra_flags[@]}" $CAD_ML_SERVICES

echo "cad-ml docker started"
echo "  API:     http://127.0.0.1:${CAD_ML_API_PORT}/api/v1/health"
echo "  Metrics: http://127.0.0.1:${CAD_ML_API_METRICS_PORT}/metrics"
