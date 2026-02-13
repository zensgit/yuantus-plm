#!/usr/bin/env bash
# =============================================================================
# YuantusPLM End-to-End Regression Test Suite
# Master script that runs all verification scripts and reports summary
# =============================================================================
set -uo pipefail

# Bash 4+ required for associative arrays on macOS.
if [[ -z "${BASH_VERSINFO[0]:-}" || "${BASH_VERSINFO[0]}" -lt 4 ]]; then
  if [[ "${YUANTUS_BASH_REEXEC:-0}" != "1" ]]; then
    if [[ -x /opt/homebrew/bin/bash ]]; then
      YUANTUS_BASH_REEXEC=1 exec /opt/homebrew/bin/bash "$0" "$@"
    elif [[ -x /usr/local/bin/bash ]]; then
      YUANTUS_BASH_REEXEC=1 exec /usr/local/bin/bash "$0" "$@"
    fi
  fi
  echo "ERROR: scripts/verify_all.sh requires bash >= 4 for associative arrays." >&2
  echo "Hint: /opt/homebrew/bin/bash scripts/verify_all.sh ..." >&2
  exit 2
fi

# Configuration
BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"
DB_URL="${DB_URL:-}"
MIGRATE_TENANT_DB="${MIGRATE_TENANT_DB:-0}"
RUN_DEDUP="${RUN_DEDUP:-0}"
START_DEDUP_STACK="${START_DEDUP_STACK:-0}"
MT_RESET="${MT_RESET:-0}"
MT_SCHEMA_PRECHECK="${MT_SCHEMA_PRECHECK:-1}"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"

# Docker compose selection (only set when START_DEDUP_STACK=1, but must be defined
# to avoid "unbound variable" errors under set -u.
USE_MT_OVERLAY=0
COMPOSE_FILES=()

load_server_env() {
  local pid_file="${REPO_ROOT}/yuantus.pid"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && ps -p "$pid" >/dev/null 2>&1; then
      local tokens
      tokens="$(ps eww -p "$pid" -o command= | tr ' ' '\n' | grep '^YUANTUS_' || true)"
      while IFS= read -r token; do
        [[ -z "$token" ]] && continue
        local key="${token%%=*}"
        local value="${token#*=}"
        case "$key" in
          YUANTUS_DATABASE_URL|YUANTUS_DATABASE_URL_TEMPLATE|YUANTUS_IDENTITY_DATABASE_URL|YUANTUS_TENANCY_MODE|YUANTUS_SCHEMA_MODE|YUANTUS_AUTH_MODE|YUANTUS_PLATFORM_ADMIN_ENABLED|YUANTUS_PLATFORM_TENANT_ID|YUANTUS_AUDIT_ENABLED|YUANTUS_CADGF_DEFAULT_EMIT|YUANTUS_DEDUP_VISION_BASE_URL)
            if [[ -z "${!key:-}" ]]; then
              export "${key}=${value}"
            fi
            ;;
        esac
      done <<< "$tokens"
    fi
  fi
}

load_server_env

load_dotenv() {
  local dotenv="${REPO_ROOT}/.env"
  if [[ ! -f "$dotenv" ]]; then
    return 0
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" == export\ * ]]; then
      line="${line#export }"
    fi
    if [[ "$line" != *=* ]]; then
      continue
    fi
    local key="${line%%=*}"
    local value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    if [[ "$key" != YUANTUS_* ]]; then
      continue
    fi
    if [[ -n "${!key:-}" ]]; then
      continue
    fi
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    export "${key}=${value}"
  done < "$dotenv"
}

load_dotenv

# Optional: start cad-ml Docker for verification runs.
CAD_ML_DOCKER_STARTED=0
cleanup_cad_ml_docker() {
  if [[ "${CAD_ML_DOCKER_STARTED:-0}" == "1" ]]; then
    echo ""
    echo "==> Stop cad-ml docker"
    "${REPO_ROOT}/scripts/stop_cad_ml_docker.sh" || true
  fi
}
trap cleanup_cad_ml_docker EXIT

if [[ "${RUN_CAD_ML_DOCKER:-0}" == "1" ]]; then
  if [[ ! -x "${REPO_ROOT}/scripts/run_cad_ml_docker.sh" || ! -x "${REPO_ROOT}/scripts/check_cad_ml_docker.sh" ]]; then
    echo "ERROR: cad-ml docker helpers not found (scripts/run_cad_ml_docker.sh)" >&2
    exit 2
  fi
  export CAD_ML_API_PORT="${CAD_ML_API_PORT:-18000}"
  export CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-http://127.0.0.1:${CAD_ML_API_PORT}}"
  export YUANTUS_CAD_ML_BASE_URL="${YUANTUS_CAD_ML_BASE_URL:-${CAD_ML_BASE_URL}}"
  echo "==> Start cad-ml docker (RUN_CAD_ML_DOCKER=1)"
  "${REPO_ROOT}/scripts/run_cad_ml_docker.sh"
  "${REPO_ROOT}/scripts/check_cad_ml_docker.sh"
  CAD_ML_DOCKER_STARTED=1
fi

# Export for child scripts
export CLI PY
export MIGRATE_TENANT_DB

# Colors (if terminal supports)
if [[ -t 1 ]]; then
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  YELLOW='\033[1;33m'
  NC='\033[0m' # No Color
else
  GREEN=''
  RED=''
  YELLOW=''
  NC=''
fi

# Results tracking
declare -A RESULTS
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0

echo "=============================================="
echo "YuantusPLM End-to-End Regression Suite"
echo "=============================================="
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "CLI: $CLI"
if [[ -n "$DB_URL" ]]; then
  echo "DB_URL: $DB_URL"
fi
echo "RUN_DEDUP: $RUN_DEDUP"
echo "START_DEDUP_STACK: $START_DEDUP_STACK"
echo "MT_RESET: $MT_RESET"
echo "MT_SCHEMA_PRECHECK: $MT_SCHEMA_PRECHECK"
if [[ -n "${RUN_CAD_ML_DOCKER:-}" || -n "${CAD_ML_BASE_URL:-}" || -n "${YUANTUS_CAD_ML_BASE_URL:-}" || -n "${CAD_PREVIEW_SAMPLE_FILE:-}" ]]; then
  echo "CAD-ML:"
  echo "  RUN_CAD_ML_DOCKER: ${RUN_CAD_ML_DOCKER:-0}"
  if [[ -n "${CAD_ML_BASE_URL:-}" || -n "${YUANTUS_CAD_ML_BASE_URL:-}" ]]; then
    echo "  CAD_ML_BASE_URL: ${CAD_ML_BASE_URL:-${YUANTUS_CAD_ML_BASE_URL:-}}"
    echo "  YUANTUS_CAD_ML_BASE_URL: ${YUANTUS_CAD_ML_BASE_URL:-}"
  fi
  if [[ -n "${CAD_PREVIEW_SAMPLE_FILE:-}" ]]; then
    echo "  CAD_PREVIEW_SAMPLE_FILE: ${CAD_PREVIEW_SAMPLE_FILE}"
  fi
  echo "  CAD_ML_HEALTH_RETRIES: ${CAD_ML_HEALTH_RETRIES:-10}"
  echo "  CAD_ML_HEALTH_SLEEP_SECONDS: ${CAD_ML_HEALTH_SLEEP_SECONDS:-2}"
fi
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|y|Y|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

run_test() {
  local name="$1"
  local script="$2"
  shift 2
  local args=("$@")

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Running: $name"
  echo "Script: $script"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ ! -x "$script" ]]; then
    echo -e "${YELLOW}SKIP${NC}: Script not found or not executable"
    RESULTS["$name"]="SKIP"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
    return 2
  fi

  # Run the script and capture exit code without aborting the suite
  "$script" "${args[@]}" 2>&1
  local exit_code=$?

  if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}PASS${NC}: $name"
    RESULTS["$name"]="PASS"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    echo -e "${RED}FAIL${NC}: $name (exit code: $exit_code)"
    RESULTS["$name"]="FAIL"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi

  return $exit_code
}

skip_test() {
  local name="$1"
  local reason="$2"
  echo -e "${YELLOW}SKIP${NC}: $name ($reason)"
  RESULTS["$name"]="SKIP"
  TOTAL_SKIP=$((TOTAL_SKIP + 1))
}

has_openapi_path() {
  local path="$1"
  local found
  found="$(
    curl -s "$BASE_URL/openapi.json" \
      | "$PY" -c 'import sys,json; data=json.load(sys.stdin); print("1" if sys.argv[1] in data.get("paths", {}) else "0")' \
        "$path" 2>/dev/null || echo "0"
  )"
  [[ "$found" == "1" ]]
}

health_field() {
  local field="$1"
  curl -s "$BASE_URL/api/v1/health" \
    | "$PY" -c 'import sys,json; data=json.load(sys.stdin); print(data.get(sys.argv[1],""))' \
      "$field" 2>/dev/null || echo ""
}

load_storage_from_health() {
  if [[ -n "${YUANTUS_STORAGE_TYPE:-}" ]]; then
    return 0
  fi
  local storage_json
  storage_json="$(
    curl -s "$BASE_URL/api/v1/health/deps" \
      | "$PY" -c 'import sys,json; data=json.load(sys.stdin); storage=data.get("deps",{}).get("storage",{}); print(json.dumps(storage))' \
        2>/dev/null || echo "{}"
  )"
  local storage_type
  storage_type="$(
    STORAGE_JSON="$storage_json" "$PY" - <<'PY'
import json, os
data = json.loads(os.environ.get("STORAGE_JSON") or "{}")
print(data.get("type",""))
PY
  )"
  if [[ -n "$storage_type" ]]; then
    export YUANTUS_STORAGE_TYPE="$storage_type"
  fi
  if [[ "$storage_type" == "local" ]]; then
    local storage_path
    storage_path="$(
      STORAGE_JSON="$storage_json" "$PY" - <<'PY'
import json, os
data = json.loads(os.environ.get("STORAGE_JSON") or "{}")
print(data.get("path",""))
PY
    )"
    if [[ -n "$storage_path" && -z "${YUANTUS_LOCAL_STORAGE_PATH:-}" ]]; then
      export YUANTUS_LOCAL_STORAGE_PATH="$storage_path"
    fi
    return 0
  fi
  if [[ "$storage_type" == "s3" ]]; then
    local endpoint_url
    local bucket_name
    endpoint_url="$(
      STORAGE_JSON="$storage_json" "$PY" - <<'PY'
import json, os
data = json.loads(os.environ.get("STORAGE_JSON") or "{}")
print(data.get("endpoint_url",""))
PY
    )"
    local effective_endpoint_url="$endpoint_url"
    if [[ -n "$endpoint_url" ]]; then
      # When the server is running in docker-compose, the internal endpoint (e.g. http://yuantus-minio:9000)
      # is not reachable from host-run verification scripts. Prefer the host-mapped port.
      if [[ "$endpoint_url" != *"localhost"* && "$endpoint_url" != *"127.0.0.1"* ]]; then
        if command -v docker >/dev/null 2>&1 && [[ -f "${REPO_ROOT}/docker-compose.yml" ]]; then
          local minio_port_line
          minio_port_line="$(docker compose -f "${REPO_ROOT}/docker-compose.yml" -p yuantusplm port minio 9000 2>/dev/null | head -n 1 || true)"
          if [[ -z "$minio_port_line" ]]; then
            minio_port_line="$(docker compose -f "${REPO_ROOT}/docker-compose.yml" port minio 9000 2>/dev/null | head -n 1 || true)"
          fi
          if [[ -n "$minio_port_line" ]]; then
            local minio_host_port
            minio_host_port="${minio_port_line##*:}"
            if [[ -n "$minio_host_port" ]]; then
              effective_endpoint_url="http://localhost:${minio_host_port}"
            fi
          fi
        fi
      fi
    fi
    bucket_name="$(
      STORAGE_JSON="$storage_json" "$PY" - <<'PY'
import json, os
data = json.loads(os.environ.get("STORAGE_JSON") or "{}")
print(data.get("bucket",""))
PY
    )"
    if [[ -n "$effective_endpoint_url" ]]; then
      if [[ -z "${YUANTUS_S3_ENDPOINT_URL:-}" ]]; then
        export YUANTUS_S3_ENDPOINT_URL="$effective_endpoint_url"
      fi
      if [[ -z "${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}" ]]; then
        export YUANTUS_S3_PUBLIC_ENDPOINT_URL="$effective_endpoint_url"
      fi
    fi
    if [[ -n "$bucket_name" && -z "${YUANTUS_S3_BUCKET_NAME:-}" ]]; then
      export YUANTUS_S3_BUCKET_NAME="$bucket_name"
    fi

    # docker-compose MinIO defaults (best-effort). Keep opt-in based on endpoint being local/minio-like.
    if [[ -z "${YUANTUS_S3_ACCESS_KEY_ID:-}" && -z "${YUANTUS_S3_SECRET_ACCESS_KEY:-}" ]]; then
      if is_truthy "${START_DEDUP_STACK:-0}" || [[ "${effective_endpoint_url:-}" == http://localhost:* || "${effective_endpoint_url:-}" == http://127.0.0.1:* ]]; then
        export YUANTUS_S3_ACCESS_KEY_ID="${YUANTUS_S3_ACCESS_KEY_ID:-minioadmin}"
        export YUANTUS_S3_SECRET_ACCESS_KEY="${YUANTUS_S3_SECRET_ACCESS_KEY:-minioadmin}"
      fi
    fi
  fi
}

wait_for_docker_postgres() {
  # Best-effort readiness wait for host-driven scripts that exec into the postgres container.
  local retries="${PG_READY_RETRIES:-30}"
  local sleep_seconds="${PG_READY_SLEEP_SECONDS:-1}"
  if [[ "${#COMPOSE_FILES[@]}" -eq 0 ]]; then
    return 0
  fi
  for ((i=1; i<=retries; i++)); do
    if docker compose "${COMPOSE_FILES[@]}" exec -T postgres pg_isready -U yuantus >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_seconds"
  done
  echo -e "${RED}ERROR${NC}: postgres not ready after ${retries}s." >&2
  return 1
}

mt_schema_precheck_pair_key() {
  # When running db-per-tenant-org in docker-compose.mt.yml, schema mode is create_all,
  # which does not alter existing DB schemas. If a tenant DB already exists with an
  # older schema (missing meta_similarity_records.pair_key), dedup ingestion can get
  # stuck. Detect and fail-fast with a reset hint.
  if [[ "${USE_MT_OVERLAY:-0}" != "1" ]]; then
    return 0
  fi
  if ! is_truthy "${MT_SCHEMA_PRECHECK:-1}"; then
    return 0
  fi

  local dbs
  dbs="$(
    docker compose "${COMPOSE_FILES[@]}" exec -T postgres \
      psql -U yuantus -d postgres -Atc "SELECT datname FROM pg_database WHERE datname LIKE 'yuantus_mt_pg__%' ORDER BY datname;" \
      2>/dev/null || true
  )"
  if [[ -z "$dbs" ]]; then
    return 0
  fi

  local drift=0
  while IFS= read -r db; do
    [[ -z "$db" ]] && continue

    local has_table
    has_table="$(
      docker compose "${COMPOSE_FILES[@]}" exec -T postgres \
        psql -U yuantus -d "$db" -Atc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='meta_similarity_records' LIMIT 1;" \
        2>/dev/null | tr -d '[:space:]' || true
    )"
    if [[ "$has_table" != "1" ]]; then
      continue
    fi

    local has_pair_key
    has_pair_key="$(
      docker compose "${COMPOSE_FILES[@]}" exec -T postgres \
        psql -U yuantus -d "$db" -Atc "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='meta_similarity_records' AND column_name='pair_key' LIMIT 1;" \
        2>/dev/null | tr -d '[:space:]' || true
    )"
    if [[ "$has_pair_key" != "1" ]]; then
      echo -e "${RED}ERROR${NC}: MT schema drift detected in ${db}: meta_similarity_records exists but pair_key is missing." >&2
      drift=1
    fi
  done <<< "$dbs"

  if [[ "$drift" == "1" ]]; then
    echo "" >&2
    echo "This usually happens when docker-compose.mt.yml runs with YUANTUS_SCHEMA_MODE=create_all." >&2
    echo "create_all does not alter existing schemas, so stale tenant DBs must be reset." >&2
    echo "" >&2
    echo "Fix (destructive):" >&2
    echo "  MT_RESET=1 RUN_DEDUP=1 START_DEDUP_STACK=1 USE_DOCKER_WORKER=1 bash scripts/verify_all.sh" >&2
    echo "Or manual:" >&2
    echo "  docker compose stop api worker && RESET=1 bash scripts/mt_pg_bootstrap.sh && docker compose up -d --build api worker" >&2
    return 1
  fi

  return 0
}

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------
echo "==> Pre-flight checks"

if is_truthy "${START_DEDUP_STACK:-0}"; then
  if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}ERROR${NC}: START_DEDUP_STACK=1 requires docker." >&2
    echo "Start the stack manually or install docker, then rerun." >&2
    exit 2
  fi
  if [[ ! -f "${REPO_ROOT}/docker-compose.yml" ]]; then
    echo -e "${RED}ERROR${NC}: Missing docker-compose.yml at ${REPO_ROOT}/docker-compose.yml" >&2
    exit 2
  fi

  if [[ -z "${YUANTUS_CAD_EXTRACTOR_MODE:-}" ]]; then
    # Local docker-compose runs usually don't have an external cad-extractor service.
    # Make cad_extract jobs fall back to built-in/local extraction by default.
    export YUANTUS_CAD_EXTRACTOR_MODE="optional"
  fi

  # Choose compose overlays based on requested tenancy mode.
  # docker-compose.yml defaults to single tenancy; db-per-tenant-org requires docker-compose.mt.yml overlay.
  USE_MT_OVERLAY=0
  COMPOSE_FILES=(-f "${REPO_ROOT}/docker-compose.yml")
  if [[ "${YUANTUS_TENANCY_MODE:-}" == "db-per-tenant-org" ]]; then
    if [[ -f "${REPO_ROOT}/docker-compose.mt.yml" ]]; then
      USE_MT_OVERLAY=1
      COMPOSE_FILES+=(-f "${REPO_ROOT}/docker-compose.mt.yml")
    else
      echo "WARN: YUANTUS_TENANCY_MODE=db-per-tenant-org but docker-compose.mt.yml not found; docker stack may be misconfigured." >&2
    fi
  fi

  echo "Starting docker compose --profile dedup stack (mt_overlay=$USE_MT_OVERLAY)..."
  if ! docker compose "${COMPOSE_FILES[@]}" --profile dedup up -d postgres minio; then
    echo -e "${RED}ERROR${NC}: Failed to start postgres/minio for dedup stack" >&2
    exit 2
  fi

  if ! wait_for_docker_postgres; then
    exit 2
  fi

  if [[ "$USE_MT_OVERLAY" == "1" ]] && is_truthy "${MT_RESET:-0}"; then
    echo "MT_RESET=1: resetting tenant/org databases (destructive)..."
    docker compose "${COMPOSE_FILES[@]}" --profile dedup stop api worker >/dev/null 2>&1 || true
    (cd "$REPO_ROOT" && RESET=1 bash scripts/mt_pg_bootstrap.sh)
  fi

  if ! mt_schema_precheck_pair_key; then
    exit 2
  fi

  if [[ "$USE_MT_OVERLAY" == "1" ]]; then
    # Multi-tenant overlay includes mt-bootstrap dependency; do not use --no-deps.
    if ! docker compose "${COMPOSE_FILES[@]}" --profile dedup up -d --build api worker; then
      echo -e "${RED}ERROR${NC}: Failed to (re)build and start api/worker for dedup stack (mt overlay)" >&2
      exit 2
    fi
  else
    if ! docker compose "${COMPOSE_FILES[@]}" --profile dedup up -d --build --no-deps api worker; then
      echo -e "${RED}ERROR${NC}: Failed to (re)build and start api/worker for dedup stack" >&2
      exit 2
    fi
  fi
  if ! docker compose "${COMPOSE_FILES[@]}" --profile dedup up -d dedup-vision; then
    echo -e "${RED}ERROR${NC}: Failed to start dedup-vision service." >&2
    echo "Hint: Ensure DEDUP_VISION_BUILD_CONTEXT is set and points to a valid dedupcad-vision checkout." >&2
    exit 2
  fi
fi

# If DB_URL is set, ensure child scripts use the same database.
if [[ -z "$DB_URL" ]]; then
  DOCKER_POSTGRES_PORT_LINE=""
  if command -v docker >/dev/null 2>&1 && [[ -f "${REPO_ROOT}/docker-compose.yml" ]]; then
    DOCKER_POSTGRES_PORT_LINE="$(docker compose -f "${REPO_ROOT}/docker-compose.yml" -p yuantusplm port postgres 5432 2>/dev/null | head -n 1 || true)"
    if [[ -z "$DOCKER_POSTGRES_PORT_LINE" ]]; then
      DOCKER_POSTGRES_PORT_LINE="$(docker compose -f "${REPO_ROOT}/docker-compose.yml" port postgres 5432 2>/dev/null | head -n 1 || true)"
    fi
  fi

  if is_truthy "${START_DEDUP_STACK:-0}" && [[ -n "$DOCKER_POSTGRES_PORT_LINE" ]]; then
    HOST_PORT="${DOCKER_POSTGRES_PORT_LINE##*:}"
    DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:${HOST_PORT}/yuantus"
    if [[ -z "${IDENTITY_DB_URL:-}" ]]; then
      IDENTITY_DB_NAME="yuantus_identity"
      if [[ "${YUANTUS_TENANCY_MODE:-}" == "db-per-tenant-org" ]]; then
        IDENTITY_DB_NAME="yuantus_identity_mt_pg"
      fi
      IDENTITY_DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:${HOST_PORT}/${IDENTITY_DB_NAME}"
    fi
  elif [[ -n "${YUANTUS_DATABASE_URL:-}" ]]; then
    DB_URL="$YUANTUS_DATABASE_URL"
  elif [[ -n "$DOCKER_POSTGRES_PORT_LINE" ]]; then
    HOST_PORT="${DOCKER_POSTGRES_PORT_LINE##*:}"
    DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:${HOST_PORT}/yuantus"
    if [[ -z "${IDENTITY_DB_URL:-}" ]]; then
      IDENTITY_DB_NAME="yuantus_identity"
      if [[ "${YUANTUS_TENANCY_MODE:-}" == "db-per-tenant-org" ]]; then
        IDENTITY_DB_NAME="yuantus_identity_mt_pg"
      fi
      IDENTITY_DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:${HOST_PORT}/${IDENTITY_DB_NAME}"
    fi
  fi
fi

if [[ -n "$DB_URL" ]]; then
  : "${YUANTUS_DATABASE_URL:=$DB_URL}"
  export YUANTUS_DATABASE_URL
  export DB_URL
fi

# Export identity DB early so CLI fallbacks (e.g. seeding admin when login fails) are consistent with the running API.
if [[ -n "${IDENTITY_DB_URL:-}" ]]; then
  : "${YUANTUS_IDENTITY_DATABASE_URL:=$IDENTITY_DB_URL}"
  export YUANTUS_IDENTITY_DATABASE_URL
  export IDENTITY_DB_URL
elif [[ -n "$DB_URL" ]]; then
  : "${YUANTUS_IDENTITY_DATABASE_URL:=$DB_URL}"
  export YUANTUS_IDENTITY_DATABASE_URL
fi

# Check CLI
if [[ ! -x "$CLI" ]]; then
  echo -e "${RED}ERROR${NC}: CLI not found at $CLI"
  echo "Set CLI=... to override"
  exit 2
fi
echo "CLI: OK"

# Check Python
if [[ ! -x "$PY" ]]; then
  echo -e "${RED}ERROR${NC}: Python not found at $PY"
  echo "Set PY=... to override"
  exit 2
fi
echo "Python: OK"

# Check API health
echo "Checking API health..."
API_HEALTH_RETRIES="${API_HEALTH_RETRIES:-}"
API_HEALTH_SLEEP_SECONDS="${API_HEALTH_SLEEP_SECONDS:-2}"
if [[ -z "$API_HEALTH_RETRIES" ]]; then
  if is_truthy "${START_DEDUP_STACK:-0}"; then
    API_HEALTH_RETRIES=60
  else
    API_HEALTH_RETRIES=1
  fi
fi

HTTP_CODE="000"
for ((i=1; i<=API_HEALTH_RETRIES; i++)); do
  HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/health" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "200" ]]; then
    break
  fi
  if (( i < API_HEALTH_RETRIES )); then
    sleep "$API_HEALTH_SLEEP_SECONDS"
  fi
done

if [[ "$HTTP_CODE" != "200" ]]; then
  echo -e "${RED}ERROR${NC}: API not reachable at $BASE_URL (HTTP $HTTP_CODE)"
  echo "Please start the server first:"
  echo "  docker compose up -d --build"
  echo "  OR"
  echo "  yuantus start --port 7910"
  exit 2
fi
echo "API Health: OK (HTTP $HTTP_CODE)"
load_storage_from_health

echo ""
echo "Pre-flight checks passed. Starting tests..."

# -----------------------------------------------------------------------------
# Quota normalization (avoid false failures in enforce/soft mode)
# -----------------------------------------------------------------------------
ADMIN_TOKEN=""
QUOTA_ADJUSTED=0
QUOTA_ORIG_JSON=""
QUOTA_RESET_JSON='{"max_users":100000,"max_orgs":10000,"max_files":1000000,"max_storage_bytes":1099511627776,"max_active_jobs":100000,"max_processing_jobs":100000}'

admin_login() {
  curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null
}

ADMIN_TOKEN="$(admin_login)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  "$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null 2>&1 || true
  ADMIN_TOKEN="$(admin_login)"
fi

if [[ -n "$ADMIN_TOKEN" ]]; then
  QUOTA_HTTP="$(curl -s -o /tmp/verify_all_quota.json -w '%{http_code}' \
    "$BASE_URL/api/v1/admin/quota" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")"
  if [[ "$QUOTA_HTTP" == "200" ]]; then
    QUOTA_MODE="$("$PY" -c 'import sys,json;print(json.load(sys.stdin).get("mode",""))' </tmp/verify_all_quota.json)"
    if [[ "$QUOTA_MODE" == "enforce" || "$QUOTA_MODE" == "soft" ]]; then
      QUOTA_ORIG_JSON="$("$PY" -c 'import sys,json;print(json.dumps(json.load(sys.stdin).get("quota") or {}))' </tmp/verify_all_quota.json)"
      curl -s -o /tmp/verify_all_quota_set.json -w '%{http_code}' \
        -X PUT "$BASE_URL/api/v1/admin/quota" \
        -H 'content-type: application/json' \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
        -d "$QUOTA_RESET_JSON" >/dev/null
      QUOTA_ADJUSTED=1
      export QUOTA_RESTORE_JSON="$QUOTA_RESET_JSON"
      echo "Quota normalization: mode=$QUOTA_MODE (set high limits for tests)"
    fi
  fi
fi

restore_quota() {
  if [[ "$QUOTA_ADJUSTED" == "1" && -n "$QUOTA_ORIG_JSON" && -n "$ADMIN_TOKEN" ]]; then
    curl -s -o /tmp/verify_all_quota_restore.json -w '%{http_code}' \
      -X PUT "$BASE_URL/api/v1/admin/quota" \
      -H 'content-type: application/json' \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
      -d "$QUOTA_ORIG_JSON" >/dev/null
    unset QUOTA_RESTORE_JSON
  fi
}

trap restore_quota EXIT

TENANCY_MODE_HEALTH="$(health_field tenancy_mode)"
AUDIT_ENABLED_HEALTH="$(health_field audit_enabled)"

# Align local CLI env with API tenancy mode to avoid stale multi-tenant settings.
if [[ "$TENANCY_MODE_HEALTH" != "db-per-tenant" && "$TENANCY_MODE_HEALTH" != "db-per-tenant-org" ]]; then
  export YUANTUS_TENANCY_MODE="single"
  unset YUANTUS_DATABASE_URL_TEMPLATE
fi

if [[ -z "${YUANTUS_TENANCY_MODE:-}" && -n "$TENANCY_MODE_HEALTH" ]]; then
  export YUANTUS_TENANCY_MODE="$TENANCY_MODE_HEALTH"
fi

if [[ -n "$DB_URL" && "$DB_URL" == postgresql* ]]; then
  DB_BASE="${DB_URL%/*}"
  if [[ -z "${DB_URL_TEMPLATE:-}" ]]; then
    if [[ "$TENANCY_MODE_HEALTH" == "db-per-tenant-org" ]]; then
      DB_URL_TEMPLATE="${DB_BASE}/yuantus_mt_pg__{tenant_id}__{org_id}"
    elif [[ "$TENANCY_MODE_HEALTH" == "db-per-tenant" ]]; then
      DB_URL_TEMPLATE="${DB_BASE}/yuantus_mt_pg__{tenant_id}"
    fi
  fi
  if [[ -z "${IDENTITY_DB_URL:-}" && "$TENANCY_MODE_HEALTH" != "single" ]]; then
    IDENTITY_DB_URL="${DB_BASE}/yuantus_identity_mt_pg"
  fi
fi

if [[ -n "${DB_URL_TEMPLATE:-}" ]]; then
  export DB_URL_TEMPLATE
  export YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"
fi
if [[ -n "${IDENTITY_DB_URL:-}" ]]; then
  export IDENTITY_DB_URL
  export YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL"
elif [[ -n "$DB_URL" ]]; then
  : "${YUANTUS_IDENTITY_DATABASE_URL:=$DB_URL}"
  export YUANTUS_IDENTITY_DATABASE_URL
fi

# -----------------------------------------------------------------------------
# Run test suites
# -----------------------------------------------------------------------------

# 0. Ops Health (deps)
if [[ -x "$SCRIPT_DIR/verify_ops_health.sh" ]]; then
  run_test "Ops Health" \
    "$SCRIPT_DIR/verify_ops_health.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 1. Run H - Basic Health & Core APIs
run_test "Run H (Core APIs)" \
  "$SCRIPT_DIR/verify_run_h.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 2. S2 - Documents & Files
run_test "S2 (Documents & Files)" \
  "$SCRIPT_DIR/verify_documents.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 2.5 Document Lifecycle
run_test "Document Lifecycle" \
  "$SCRIPT_DIR/verify_document_lifecycle.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 2.6 Part Lifecycle
run_test "Part Lifecycle" \
  "$SCRIPT_DIR/verify_part_lifecycle.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 2.7 Lifecycle Suspended
if [[ -x "$SCRIPT_DIR/verify_lifecycle_suspended.sh" ]]; then
  run_test "Lifecycle Suspended" \
    "$SCRIPT_DIR/verify_lifecycle_suspended.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 3. S1 - Meta Schema + RBAC
run_test "S1 (Meta + RBAC)" \
  "$SCRIPT_DIR/verify_permissions.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 4. S7 - Quotas
run_test "S7 (Quotas)" \
  "$SCRIPT_DIR/verify_quotas.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 5. S3.1 - BOM Tree + Cycle Detection
run_test "S3.1 (BOM Tree)" \
  "$SCRIPT_DIR/verify_bom_tree.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 6. S3.2 - BOM Effectivity
run_test "S3.2 (BOM Effectivity)" \
  "$SCRIPT_DIR/verify_bom_effectivity.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 6.0 Effectivity Extended (Lot/Serial)
if [[ -x "$SCRIPT_DIR/verify_effectivity_extended.sh" ]]; then
  run_test "Effectivity Extended" \
    "$SCRIPT_DIR/verify_effectivity_extended.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 6.0.1 BOM Obsolete Handling
if [[ -x "$SCRIPT_DIR/verify_bom_obsolete.sh" ]]; then
  run_test "BOM Obsolete" \
    "$SCRIPT_DIR/verify_bom_obsolete.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 6.0.2 BOM Weight Rollup
if [[ -x "$SCRIPT_DIR/verify_bom_weight_rollup.sh" ]]; then
  run_test "BOM Weight Rollup" \
    "$SCRIPT_DIR/verify_bom_weight_rollup.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 6.1 S12 - Configuration/Variant BOM (optional)
if [[ -x "$SCRIPT_DIR/verify_config_variants.sh" ]]; then
  if [[ "${RUN_CONFIG_VARIANTS:-0}" == "1" ]]; then
    run_test "S12 (Config Variants)" \
      "$SCRIPT_DIR/verify_config_variants.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "S12 (Config Variants)" "RUN_CONFIG_VARIANTS=0"
  fi
fi

# 7. S3.3 - Version Semantics
run_test "S3.3 (Versions)" \
  "$SCRIPT_DIR/verify_versions.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 8. S4 - ECO Advanced
run_test "S4 (ECO Advanced)" \
  "$SCRIPT_DIR/verify_eco_advanced.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 9. S5-A - CAD Pipeline S3
run_test "S5-A (CAD Pipeline S3)" \
  "$SCRIPT_DIR/verify_cad_pipeline_s3.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 9.1 S5-A - CAD 2D Preview (DWG/DXF render)
if [[ -x "$SCRIPT_DIR/verify_cad_preview_2d.sh" ]]; then
  run_test "S5-A (CAD 2D Preview)" \
    "$SCRIPT_DIR/verify_cad_preview_2d.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 9.1b S5-A - CADGF Preview Public Base (local, optional)
if [[ -x "$SCRIPT_DIR/verify_cad_preview_public_base.sh" ]]; then
  if [[ "${RUN_CADGF_PUBLIC_BASE:-0}" == "1" ]]; then
    run_test "S5-A (CADGF Public Base)" \
      "$SCRIPT_DIR/verify_cad_preview_public_base.sh" || true
  else
    skip_test "S5-A (CADGF Public Base)" "RUN_CADGF_PUBLIC_BASE=0"
  fi
fi

# 9.1c S5-A - CADGF Preview Online (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_preview_online.sh" ]]; then
  if [[ "${RUN_CADGF_PREVIEW_ONLINE:-0}" == "1" ]]; then
    if [[ -n "${CADGF_PREVIEW_SAMPLE_FILE:-}" && -f "$CADGF_PREVIEW_SAMPLE_FILE" ]]; then
      export BASE_URL TENANT ORG
      export LOGIN_USERNAME="${CADGF_PREVIEW_USERNAME:-admin}"
      export PASSWORD="${CADGF_PREVIEW_PASSWORD:-admin}"
      export SAMPLE_FILE="$CADGF_PREVIEW_SAMPLE_FILE"
      if [[ -n "${CADGF_EXPECT_METADATA+x}" ]]; then
        export EXPECT_METADATA="${CADGF_EXPECT_METADATA}"
      elif [[ "${YUANTUS_CADGF_DEFAULT_EMIT:-}" == *"meta"* ]]; then
        export EXPECT_METADATA="1"
      else
        export EXPECT_METADATA="0"
      fi
      run_test "S5-A (CADGF Preview Online)" \
        "$SCRIPT_DIR/verify_cad_preview_online.sh" || true
      unset LOGIN_USERNAME PASSWORD SAMPLE_FILE EXPECT_METADATA
    else
      skip_test "S5-A (CADGF Preview Online)" "CADGF_PREVIEW_SAMPLE_FILE missing"
    fi
  else
    skip_test "S5-A (CADGF Preview Online)" "RUN_CADGF_PREVIEW_ONLINE=0"
  fi
fi

# 10. S5-B - CAD 2D Connectors (GStarCAD/ZWCAD)
run_test "S5-B (CAD 2D Connectors)" \
  "$SCRIPT_DIR/verify_cad_connectors_2d.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 10.0b S5-B - CAD 2D Real Connectors (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_connectors_real_2d.sh" ]]; then
  if [[ "${RUN_CAD_REAL_CONNECTORS_2D:-0}" == "1" ]]; then
    run_test "S5-B (CAD 2D Real Connectors)" \
      "$SCRIPT_DIR/verify_cad_connectors_real_2d.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "S5-B (CAD 2D Real Connectors)" "RUN_CAD_REAL_CONNECTORS_2D=0"
  fi
fi

# 10.1 S5-B - CAD 3D Connectors (SolidWorks/NX/Creo/CATIA/Inventor)
if [[ -x "$SCRIPT_DIR/verify_cad_connectors_3d.sh" ]]; then
  run_test "S5-B (CAD 3D Connectors)" \
    "$SCRIPT_DIR/verify_cad_connectors_3d.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 11. S5-C - CAD Attribute Sync (x-cad-synced mapping)
run_test "S5-C (CAD Attribute Sync)" \
  "$SCRIPT_DIR/verify_cad_sync.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 11.0b S5-C - CAD OCR Title Block (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_ocr_titleblock.sh" ]]; then
  run_test "S5-C (CAD OCR Title Block)" \
    "$SCRIPT_DIR/verify_cad_ocr_titleblock.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 11.0c S5-C - CAD Filename Parsing (local)
if [[ -x "$SCRIPT_DIR/verify_cad_filename_parse.sh" ]]; then
  run_test "S5-C (CAD Filename Parsing)" \
    "$SCRIPT_DIR/verify_cad_filename_parse.sh" || true
fi

# 11.0d S5-C - CAD Attribute Normalization (local)
if [[ -x "$SCRIPT_DIR/verify_cad_attribute_normalization.sh" ]]; then
  run_test "S5-C (CAD Attribute Normalization)" \
    "$SCRIPT_DIR/verify_cad_attribute_normalization.sh" || true
fi

# 11.0e S5-B - CAD 2D Connector Coverage (offline, optional)
if [[ -x "$SCRIPT_DIR/verify_cad_connector_coverage_2d.sh" ]]; then
  if [[ "${RUN_CAD_CONNECTOR_COVERAGE_2D:-0}" == "1" ]]; then
    if [[ -n "${CAD_CONNECTOR_COVERAGE_DIR:-}" && -d "$CAD_CONNECTOR_COVERAGE_DIR" ]]; then
      run_test "S5-B (CAD 2D Connector Coverage)" \
        "$SCRIPT_DIR/verify_cad_connector_coverage_2d.sh" || true
    else
      skip_test "S5-B (CAD 2D Connector Coverage)" "CAD_CONNECTOR_COVERAGE_DIR not set or missing"
    fi
  else
    skip_test "S5-B (CAD 2D Connector Coverage)" "RUN_CAD_CONNECTOR_COVERAGE_2D=0"
  fi
fi

# 11.1 S5-B - CAD Connectors Config (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_connectors_config.sh" ]]; then
  if has_openapi_path "/api/v1/cad/connectors/reload"; then
    run_test "S5-B (CAD Connectors Config)" \
      "$SCRIPT_DIR/verify_cad_connectors_config.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "S5-B (CAD Connectors Config)" "endpoint not available"
  fi
fi

# 11.2 S5-C - CAD Sync Template (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_sync_template.sh" ]]; then
  if has_openapi_path "/api/v1/cad/sync-template/{item_type_id}"; then
    run_test "S5-C (CAD Sync Template)" \
      "$SCRIPT_DIR/verify_cad_sync_template.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "S5-C (CAD Sync Template)" "endpoint not available"
  fi
fi

# 11.2b S5-C - CAD Auto Part (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_auto_part.sh" ]]; then
  if [[ "${RUN_CAD_AUTO_PART:-0}" == "1" ]]; then
    run_test "S5-C (CAD Auto Part)" \
      "$SCRIPT_DIR/verify_cad_auto_part.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "S5-C (CAD Auto Part)" "RUN_CAD_AUTO_PART=0"
  fi
fi

# 11.3 S5-C - CAD Extractor Stub (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_extractor_stub.sh" ]]; then
  if [[ "${RUN_CAD_EXTRACTOR_STUB:-0}" == "1" ]]; then
    run_test "S5-C (CAD Extractor Stub)" \
      "$SCRIPT_DIR/verify_cad_extractor_stub.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "S5-C (CAD Extractor Stub)" "RUN_CAD_EXTRACTOR_STUB=0"
  fi
fi

# 11.4 S5-C - CAD Extractor External (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_extractor_external.sh" ]]; then
  if [[ "${RUN_CAD_EXTRACTOR_EXTERNAL:-0}" == "1" ]]; then
    run_test "S5-C (CAD Extractor External)" \
      "$SCRIPT_DIR/verify_cad_extractor_external.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "S5-C (CAD Extractor External)" "RUN_CAD_EXTRACTOR_EXTERNAL=0"
  fi
fi

# 11.5 S5-C - CAD Extractor Service (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_extractor_service.sh" ]]; then
  if [[ "${RUN_CAD_EXTRACTOR_SERVICE:-0}" == "1" ]]; then
    CAD_EXTRACTOR_BASE="${CAD_EXTRACTOR_BASE_URL:-http://127.0.0.1:${CAD_EXTRACTOR_PORT:-8200}}"
    run_test "S5-C (CAD Extractor Service)" \
      "$SCRIPT_DIR/verify_cad_extractor_service.sh" \
      "$CAD_EXTRACTOR_BASE" || true
  else
    skip_test "S5-C (CAD Extractor Service)" "RUN_CAD_EXTRACTOR_SERVICE=0"
  fi
fi

# 11.6 CAD Real Samples (optional)
if [[ -x "$SCRIPT_DIR/verify_cad_real_samples.sh" ]]; then
  if [[ "${RUN_CAD_REAL_SAMPLES:-0}" == "1" ]]; then
    run_test "CAD Real Samples" \
      "$SCRIPT_DIR/verify_cad_real_samples.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "CAD Real Samples" "RUN_CAD_REAL_SAMPLES=0"
  fi
fi

# 11.7 CAD Dedup (S3 + Dedup Vision) (optional)
if [[ "${RUN_DEDUP:-0}" == "1" ]]; then
  if [[ "${YUANTUS_STORAGE_TYPE:-}" != "s3" ]]; then
    skip_test "CAD Dedup Vision (S3)" "storage_type=${YUANTUS_STORAGE_TYPE:-<empty>} (requires s3)"
    skip_test "CAD Dedup Relationship (S3)" "storage_type=${YUANTUS_STORAGE_TYPE:-<empty>} (requires s3)"
  else
    if [[ -x "$SCRIPT_DIR/verify_cad_dedup_vision_s3.sh" ]]; then
      run_test "CAD Dedup Vision (S3)" \
        "$SCRIPT_DIR/verify_cad_dedup_vision_s3.sh" \
        "$BASE_URL" "$TENANT" "$ORG" || true
    else
      skip_test "CAD Dedup Vision (S3)" "script not found"
    fi
    if [[ -x "$SCRIPT_DIR/verify_cad_dedup_relationship_s3.sh" ]]; then
      run_test "CAD Dedup Relationship (S3)" \
        "$SCRIPT_DIR/verify_cad_dedup_relationship_s3.sh" \
        "$BASE_URL" "$TENANT" "$ORG" || true
    else
      skip_test "CAD Dedup Relationship (S3)" "script not found"
    fi
  fi
else
  skip_test "CAD Dedup Vision (S3)" "RUN_DEDUP=0"
  skip_test "CAD Dedup Relationship (S3)" "RUN_DEDUP=0"
fi

# 12. S6 - Search Index (optional)
if [[ -x "$SCRIPT_DIR/verify_search_index.sh" ]]; then
  run_test "Search Index" \
    "$SCRIPT_DIR/verify_search_index.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 12.1 S6 - Search Reindex (optional)
if [[ -x "$SCRIPT_DIR/verify_search_reindex.sh" ]]; then
  run_test "Search Reindex" \
    "$SCRIPT_DIR/verify_search_reindex.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 12.2 S6 - Search ECO (optional)
if [[ -x "$SCRIPT_DIR/verify_search_eco.sh" ]]; then
  run_test "Search ECO" \
    "$SCRIPT_DIR/verify_search_eco.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 13. S6 - Reports Summary (optional)
if [[ -x "$SCRIPT_DIR/verify_reports_summary.sh" ]]; then
  run_test "Reports Summary" \
    "$SCRIPT_DIR/verify_reports_summary.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 14. Audit Logs (optional; requires AUDIT_ENABLED)
if [[ -x "$SCRIPT_DIR/verify_audit_logs.sh" ]]; then
  if [[ "$AUDIT_ENABLED_HEALTH" == "true" || "$AUDIT_ENABLED_HEALTH" == "True" ]]; then
    run_test "Audit Logs" \
      "$SCRIPT_DIR/verify_audit_logs.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "Audit Logs" "audit_enabled=$AUDIT_ENABLED_HEALTH"
  fi
fi

# 14.1 S8 - Ops Monitoring (optional; requires AUDIT_ENABLED + platform admin)
if [[ -x "$SCRIPT_DIR/verify_ops_s8.sh" ]]; then
  if [[ "${RUN_OPS_S8:-0}" == "1" ]]; then
    if [[ "$AUDIT_ENABLED_HEALTH" == "true" || "$AUDIT_ENABLED_HEALTH" == "True" ]]; then
      VERIFY_QUOTA_MONITORING=1 VERIFY_RETENTION_ENDPOINTS=1 \
        run_test "S8 (Ops Monitoring)" \
        "$SCRIPT_DIR/verify_ops_s8.sh" \
        "$BASE_URL" "$TENANT" "$ORG" || true
    else
      skip_test "S8 (Ops Monitoring)" "audit_enabled=$AUDIT_ENABLED_HEALTH"
    fi
  else
    skip_test "S8 (Ops Monitoring)" "RUN_OPS_S8=0"
  fi
fi

# 15. S7 - Multi-Tenancy (only when TENANCY_MODE is enabled)
if [[ "$TENANCY_MODE_HEALTH" == "db-per-tenant" || "$TENANCY_MODE_HEALTH" == "db-per-tenant-org" ]]; then
  run_test "S7 (Multi-Tenancy)" \
    "$SCRIPT_DIR/verify_multitenancy.sh" \
    "$BASE_URL" "$TENANT" "tenant-2" "$ORG" "org-2" || true
else
  skip_test "S7 (Multi-Tenancy)" "tenancy_mode=$TENANCY_MODE_HEALTH"
fi

# 15.1 S7 - Tenant Provisioning (optional)
if [[ -x "$SCRIPT_DIR/verify_tenant_provisioning.sh" ]]; then
  if [[ "${RUN_TENANT_PROVISIONING:-0}" == "1" ]]; then
    run_test "S7 (Tenant Provisioning)" \
      "$SCRIPT_DIR/verify_tenant_provisioning.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "S7 (Tenant Provisioning)" "RUN_TENANT_PROVISIONING=0"
  fi
fi

# 16. Where-Used (if exists)
if [[ -x "$SCRIPT_DIR/verify_where_used.sh" ]]; then
  run_test "Where-Used API" \
    "$SCRIPT_DIR/verify_where_used.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 16.1 UI Aggregation (optional)
if [[ "${RUN_UI_AGG:-0}" == "1" ]]; then
  if [[ -x "$SCRIPT_DIR/verify_product_detail.sh" ]]; then
    run_test "UI Product Detail" \
      "$SCRIPT_DIR/verify_product_detail.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  fi
  if [[ -x "$SCRIPT_DIR/verify_product_ui.sh" ]]; then
    run_test "UI Product Summary" \
      "$SCRIPT_DIR/verify_product_ui.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  fi
  if [[ -x "$SCRIPT_DIR/verify_where_used_ui.sh" ]]; then
    run_test "UI Where-Used" \
      "$SCRIPT_DIR/verify_where_used_ui.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  fi
  if [[ -x "$SCRIPT_DIR/verify_bom_ui.sh" ]]; then
    run_test "UI BOM" \
      "$SCRIPT_DIR/verify_bom_ui.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  fi
  if [[ -x "$SCRIPT_DIR/verify_docs_approval.sh" ]]; then
    run_test "UI Docs Approval" \
      "$SCRIPT_DIR/verify_docs_approval.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  fi
  if [[ -x "$SCRIPT_DIR/verify_docs_eco_ui.sh" ]]; then
    run_test "UI Docs ECO Summary" \
      "$SCRIPT_DIR/verify_docs_eco_ui.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  fi

  if [[ "${RUN_UI_PLAYWRIGHT:-0}" == "1" ]]; then
    if command -v npx >/dev/null 2>&1 && [[ -x "$REPO_ROOT/node_modules/.bin/playwright" ]]; then
      run_test "UI Playwright Summaries" \
        "$SCRIPT_DIR/verify_playwright_product_ui_summaries.sh" \
        "$BASE_URL" || true
    else
      skip_test "UI Playwright Summaries" "playwright not installed"
    fi
  else
    skip_test "UI Playwright Summaries" "RUN_UI_PLAYWRIGHT=0"
  fi
else
  skip_test "UI Product Detail" "RUN_UI_AGG=0"
  skip_test "UI Product Summary" "RUN_UI_AGG=0"
  skip_test "UI Where-Used" "RUN_UI_AGG=0"
  skip_test "UI BOM" "RUN_UI_AGG=0"
  skip_test "UI Docs Approval" "RUN_UI_AGG=0"
  skip_test "UI Docs ECO Summary" "RUN_UI_AGG=0"
  skip_test "UI Playwright Summaries" "RUN_UI_AGG=0"
fi

# 17. BOM Compare (skip if endpoint not available)
if [[ -x "$SCRIPT_DIR/verify_bom_compare.sh" ]]; then
  if has_openapi_path "/api/v1/bom/compare"; then
    run_test "BOM Compare" \
      "$SCRIPT_DIR/verify_bom_compare.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "BOM Compare" "endpoint not available"
  fi
fi

# 17.1 BOM Compare Field Contract (schema + normalized fields)
if [[ -x "$SCRIPT_DIR/verify_bom_compare_fields.sh" ]]; then
  if has_openapi_path "/api/v1/bom/compare/schema"; then
    run_test "BOM Compare Field Contract" \
      "$SCRIPT_DIR/verify_bom_compare_fields.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "BOM Compare Field Contract" "endpoint not available"
  fi
fi

# 17.2 Where-Used Line Schema
if [[ -x "$SCRIPT_DIR/verify_where_used_schema.sh" ]]; then
  if has_openapi_path "/api/v1/bom/where-used/schema"; then
    run_test "Where-Used Line Schema" \
      "$SCRIPT_DIR/verify_where_used_schema.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "Where-Used Line Schema" "endpoint not available"
  fi
fi

# 18. Baseline (BOM Snapshot)
if [[ -x "$SCRIPT_DIR/verify_baseline.sh" ]]; then
  if has_openapi_path "/api/v1/baselines"; then
    run_test "Baseline" \
      "$SCRIPT_DIR/verify_baseline.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "Baseline" "endpoint not available"
  fi
fi

# 18.1 Baseline Filters (list filtering contract)
if [[ -x "$SCRIPT_DIR/verify_baseline_filters.sh" ]]; then
  if has_openapi_path "/api/v1/baselines"; then
    run_test "Baseline Filters" \
      "$SCRIPT_DIR/verify_baseline_filters.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "Baseline Filters" "endpoint not available"
  fi
fi

# 19. BOM Substitutes (skip if endpoint not available)
if [[ -x "$SCRIPT_DIR/verify_substitutes.sh" ]]; then
  if has_openapi_path "/api/v1/bom/{bom_line_id}/substitutes"; then
    run_test "BOM Substitutes" \
      "$SCRIPT_DIR/verify_substitutes.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "BOM Substitutes" "endpoint not available"
  fi
fi

# 20. MBOM Convert (skip if endpoint not available)
if [[ -x "$SCRIPT_DIR/verify_mbom_convert.sh" ]]; then
  if has_openapi_path "/api/v1/bom/convert/ebom-to-mbom"; then
    run_test "MBOM Convert" \
      "$SCRIPT_DIR/verify_mbom_convert.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "MBOM Convert" "endpoint not available"
  fi
fi

# 21. Item Equivalents (skip if endpoint not available)
if [[ -x "$SCRIPT_DIR/verify_equivalents.sh" ]]; then
  if has_openapi_path "/api/v1/items/{item_id}/equivalents"; then
    run_test "Item Equivalents" \
      "$SCRIPT_DIR/verify_equivalents.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "Item Equivalents" "endpoint not available"
  fi
fi

# 22. Version-File Binding (skip if endpoint not available)
if [[ -x "$SCRIPT_DIR/verify_version_files.sh" ]]; then
  if has_openapi_path "/api/v1/versions/{version_id}/files"; then
    run_test "Version-File Binding" \
      "$SCRIPT_DIR/verify_version_files.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "Version-File Binding" "endpoint not available"
  fi
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "REGRESSION TEST SUMMARY"
echo "=============================================="
echo ""

# Print results table
printf "%-25s %s\n" "Test Suite" "Result"
printf "%-25s %s\n" "-------------------------" "------"

for name in "Ops Health" "Run H (Core APIs)" "S2 (Documents & Files)" "Document Lifecycle" "Part Lifecycle" "Lifecycle Suspended" "S1 (Meta + RBAC)" "S7 (Quotas)" "S3.1 (BOM Tree)" "S3.2 (BOM Effectivity)" "Effectivity Extended" "BOM Obsolete" "BOM Weight Rollup" "S12 (Config Variants)" "S3.3 (Versions)" "S4 (ECO Advanced)" "S5-A (CAD Pipeline S3)" "S5-B (CAD 2D Connectors)" "S5-B (CAD 2D Real Connectors)" "S5-B (CAD 2D Connector Coverage)" "S5-C (CAD Attribute Sync)" "S5-B (CAD Connectors Config)" "S5-C (CAD Sync Template)" "S5-C (CAD Auto Part)" "S5-C (CAD Extractor Stub)" "S5-C (CAD Extractor External)" "S5-C (CAD Extractor Service)" "CAD Real Samples" "CAD Dedup Vision (S3)" "CAD Dedup Relationship (S3)" "Search Index" "Search Reindex" "Search ECO" "Reports Summary" "Audit Logs" "S8 (Ops Monitoring)" "S7 (Multi-Tenancy)" "S7 (Tenant Provisioning)" "Where-Used API" "UI Product Detail" "UI Product Summary" "UI Where-Used" "UI BOM" "UI Docs Approval" "UI Docs ECO Summary" "BOM Compare" "Baseline" "Baseline Filters" "BOM Substitutes" "MBOM Convert" "Item Equivalents" "Version-File Binding"; do
  result="${RESULTS[$name]:-N/A}"
  case "$result" in
    PASS) printf "%-25s ${GREEN}%s${NC}\n" "$name" "$result" ;;
    FAIL) printf "%-25s ${RED}%s${NC}\n" "$name" "$result" ;;
    SKIP) printf "%-25s ${YELLOW}%s${NC}\n" "$name" "$result" ;;
    *)    printf "%-25s %s\n" "$name" "$result" ;;
  esac
done

echo ""
echo "----------------------------------------------"
printf "PASS: ${GREEN}%d${NC}  FAIL: ${RED}%d${NC}  SKIP: ${YELLOW}%d${NC}\n" "$TOTAL_PASS" "$TOTAL_FAIL" "$TOTAL_SKIP"
echo "----------------------------------------------"

# Exit with appropriate code
if [[ $TOTAL_FAIL -gt 0 ]]; then
  echo ""
  echo -e "${RED}REGRESSION FAILED${NC}"
  exit 1
else
  echo ""
  echo -e "${GREEN}ALL TESTS PASSED${NC}"
  exit 0
fi
