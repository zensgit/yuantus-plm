#!/usr/bin/env bash
# =============================================================================
# Render-service backport deploy/smoke helper for release/prod-0.1.3-20260415.
#
# Default mode is preflight-only: validate Docker/compose/render env and print
# the deploy commands. Pass --deploy to build/restart api+worker.
# =============================================================================
set -euo pipefail

PROJECT="${PROJECT:-yuantusplm}"
BASE_URL="${BASE_URL:-http://127.0.0.1:7910}"
RENDER_LOG_SERVICE="${RENDER_LOG_SERVICE:-render-service}"
DEPLOY=0

usage() {
  cat <<'EOF'
Usage:
  scripts/render_service_backport_smoke.sh [--deploy]

Environment:
  YUANTUS_RENDER_SERVICE_BASE_URL   Required to enable VemCAD render service.
  PROJECT                           Compose project name (default: yuantusplm).
  BASE_URL                          API base URL for health check (default: http://127.0.0.1:7910).
  RENDER_LOG_SERVICE                Render service container name for log hints (default: render-service).

Default mode only runs preflight and prints commands. --deploy performs:
  docker compose build api worker
  docker compose up -d api worker
  curl /api/v1/health

After --deploy, upload a real DXF through the product UI/API and confirm:
  docker logs --tail=200 "$RENDER_LOG_SERVICE" | grep 'POST /render'
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --deploy)
      DEPLOY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 2
  fi
}

need_cmd docker
need_cmd curl

if [[ -z "${YUANTUS_RENDER_SERVICE_BASE_URL:-}" ]]; then
  cat >&2 <<'EOF'
YUANTUS_RENDER_SERVICE_BASE_URL is not set.
Set it to the render service URL reachable from api/worker containers, for example:
  export YUANTUS_RENDER_SERVICE_BASE_URL=http://render-service:8077
EOF
  exit 2
fi

if [[ ! -f docker-compose.yml ]]; then
  echo "Run this from the repository root containing docker-compose.yml." >&2
  exit 2
fi

echo "==> Preflight"
echo "project=$PROJECT"
echo "base_url=$BASE_URL"
echo "render_service_base_url=$YUANTUS_RENDER_SERVICE_BASE_URL"
docker compose -p "$PROJECT" config >/dev/null
docker compose -p "$PROJECT" ps || true

echo ""
echo "==> Compose render env check"
COMPOSE_CONFIG="$(docker compose -p "$PROJECT" config)"
for token in \
  "YUANTUS_RENDER_SERVICE_BASE_URL" \
  "YUANTUS_RENDER_SERVICE_TIMEOUT_SECONDS" \
  "YUANTUS_CIRCUIT_BREAKER_RENDER_SERVICE_ENABLED"; do
  if ! grep -Fq "$token" <<<"$COMPOSE_CONFIG"; then
    echo "Rendered compose config is missing $token" >&2
    exit 1
  fi
done
echo "compose render env present"

if [[ "$DEPLOY" != "1" ]]; then
  cat <<EOF

Preflight passed. To deploy on this host:
  export YUANTUS_RENDER_SERVICE_BASE_URL=${YUANTUS_RENDER_SERVICE_BASE_URL}
  scripts/render_service_backport_smoke.sh --deploy

Manual smoke after deploy:
  1. Upload a real DXF and request/generate preview.
  2. Confirm render service log contains POST /render:
     docker logs --tail=200 ${RENDER_LOG_SERVICE} | grep 'POST /render'
  3. Confirm the PLM preview is visible.
EOF
  exit 0
fi

echo ""
echo "==> Rollback image tags for currently running api/worker, if present"
TS="$(date -u +%Y%m%d%H%M%S)"
for svc in api worker; do
  cid="$(docker compose -p "$PROJECT" ps -q "$svc" || true)"
  if [[ -n "$cid" ]]; then
    image_id="$(docker inspect -f '{{.Image}}' "$cid")"
    tag="${PROJECT}-${svc}:rollback-${TS}"
    docker tag "$image_id" "$tag"
    echo "$svc rollback tag: $tag"
  else
    echo "$svc not currently running; no rollback tag created"
  fi
done

echo ""
echo "==> Build api/worker"
docker compose -p "$PROJECT" build api worker

echo ""
echo "==> Restart api/worker"
docker compose -p "$PROJECT" up -d api worker

echo ""
echo "==> API health"
curl -fsS "$BASE_URL/api/v1/health"
echo ""

cat <<EOF

Deploy step completed. Finish smoke manually:
  1. Upload a real DXF and request/generate preview.
  2. Confirm render service log contains POST /render:
     docker logs --tail=200 ${RENDER_LOG_SERVICE} | grep 'POST /render'
  3. Confirm the PLM preview is visible.

Rollback tags created with timestamp ${TS}; if needed, retag those images back
to your deployment image tags and restart api/worker.
EOF
