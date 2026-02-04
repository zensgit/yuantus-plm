#!/usr/bin/env bash
# =============================================================================
# One-click stop for cad-ml-platform (Docker compose)
# =============================================================================
set -euo pipefail

CAD_ML_REPO="${CAD_ML_REPO:-/Users/huazhou/Downloads/Github/cad-ml-platform}"
CAD_ML_COMPOSE_FILE="${CAD_ML_COMPOSE_FILE:-deployments/docker/docker-compose.yml}"
CAD_ML_REMOVE_VOLUMES="${CAD_ML_REMOVE_VOLUMES:-0}"
CAD_ML_REMOVE_ORPHANS="${CAD_ML_REMOVE_ORPHANS:-0}"

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

extra_flags=()
if [[ "$CAD_ML_REMOVE_VOLUMES" == "1" ]]; then
  extra_flags+=(-v)
fi
if [[ "$CAD_ML_REMOVE_ORPHANS" == "1" ]]; then
  extra_flags+=(--remove-orphans)
fi

"${compose_cmd[@]}" down "${extra_flags[@]}"
echo "cad-ml docker stopped"
