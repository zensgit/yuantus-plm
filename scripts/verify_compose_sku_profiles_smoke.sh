#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: verify_compose_sku_profiles_smoke.sh PROFILE

Start a minimal docker-compose stack for one SKU profile, wait for health
checks, then tear it down.

Profiles:
  base
  collab
  combined

Environment:
  METASHEET2_ROOT      Path to sibling metasheet2 checkout for the combined profile.
                       Default: ../metasheet2 (relative to the Yuantus repo root)
  KEEP_UP              When set to 1, keep the compose project running after success.
  SMOKE_PROJECT_NAME   Optional explicit docker compose project name.
  SMOKE_START_TIMEOUT  Health wait timeout in seconds. Default: 180

Ports expected on the host:
  Yuantus API          7910
  Postgres             55432
  MinIO API/Console    59000 / 59001
  Metasheet backend    7778 (combined only)
  Metasheet web        8899 (combined only)
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

wait_http_ok() {
  local url="$1"
  local timeout="$2"
  local started_at
  started_at="$(date +%s)"

  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    if (( "$(date +%s)" - started_at >= timeout )); then
      return 1
    fi
    sleep 2
  done
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROFILE="${1:-}"
if [[ -z "${PROFILE}" ]]; then
  usage
  exit 1
fi
if [[ "${PROFILE}" == "--help" || "${PROFILE}" == "-h" ]]; then
  usage
  exit 0
fi

case "${PROFILE}" in
  base|collab|combined)
    ;;
  *)
    die "Unsupported profile: ${PROFILE}"
    ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  die "docker is required"
fi
if ! docker compose version >/dev/null 2>&1; then
  die "docker compose plugin is required"
fi
if ! docker info >/dev/null 2>&1; then
  die "Docker daemon is not running"
fi

ROOT_FILE="${REPO_ROOT}/docker-compose.yml"
OVERLAY_FILE="${REPO_ROOT}/docker-compose.profile-${PROFILE}.yml"
VERIFY_SCRIPT="${REPO_ROOT}/scripts/verify_compose_sku_profiles.sh"
[[ -f "${ROOT_FILE}" ]] || die "Missing ${ROOT_FILE}"
[[ -f "${OVERLAY_FILE}" ]] || die "Missing ${OVERLAY_FILE}"
[[ -f "${VERIFY_SCRIPT}" ]] || die "Missing ${VERIFY_SCRIPT}"

COMPOSE_PROJECT_NAME="${SMOKE_PROJECT_NAME:-yuantussku${PROFILE}$(date +%s)}"
export COMPOSE_PROJECT_NAME
SMOKE_START_TIMEOUT="${SMOKE_START_TIMEOUT:-180}"

if [[ "${PROFILE}" == "combined" ]]; then
  METASHEET2_ROOT="${METASHEET2_ROOT:-${REPO_ROOT}/../metasheet2}"
  export METASHEET2_ROOT
  [[ -d "${METASHEET2_ROOT}" ]] || die "METASHEET2_ROOT does not exist: ${METASHEET2_ROOT}"
fi

cleanup() {
  if [[ "${KEEP_UP:-0}" == "1" ]]; then
    echo "KEEP_UP=1; leaving compose project running: ${COMPOSE_PROJECT_NAME}" >&2
    return
  fi
  docker compose -f "${ROOT_FILE}" -f "${OVERLAY_FILE}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

bash "${VERIFY_SCRIPT}" --render "${PROFILE}" >/dev/null

docker compose -f "${ROOT_FILE}" -f "${OVERLAY_FILE}" up -d --build

wait_http_ok "http://127.0.0.1:7910/api/v1/health" "${SMOKE_START_TIMEOUT}" \
  || die "Yuantus API did not become healthy within ${SMOKE_START_TIMEOUT}s"

if [[ "${PROFILE}" == "combined" ]]; then
  wait_http_ok "http://127.0.0.1:7778/health" "${SMOKE_START_TIMEOUT}" \
    || die "Metasheet backend did not become healthy within ${SMOKE_START_TIMEOUT}s"
  wait_http_ok "http://127.0.0.1:8899/" "${SMOKE_START_TIMEOUT}" \
    || die "Metasheet web did not become healthy within ${SMOKE_START_TIMEOUT}s"
fi

echo "profile=${PROFILE} project=${COMPOSE_PROJECT_NAME} smoke=ok"
