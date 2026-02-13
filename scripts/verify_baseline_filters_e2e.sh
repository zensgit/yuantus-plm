#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Baseline list filters.
#
# Coverage:
# - create a baseline with explicit baseline_type/scope/state/effective_date
# - list baselines filtered by baseline_type/scope/state
# - list baselines filtered by effective date range (effective_from/to)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-baseline-filters/${timestamp}"
OUT_DIR="${OUT_DIR:-$OUT_DIR_DEFAULT}"
mkdir -p "$OUT_DIR"

log() { echo "[$(date +%H:%M:%S)] $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

PY_BIN="${PY_BIN:-${REPO_ROOT}/.venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="python3"
fi

YUANTUS_BIN="${YUANTUS_BIN:-${REPO_ROOT}/.venv/bin/yuantus}"
if [[ ! -x "$YUANTUS_BIN" ]]; then
  YUANTUS_BIN="yuantus"
fi

UVICORN_BIN="${UVICORN_BIN:-${REPO_ROOT}/.venv/bin/uvicorn}"
if [[ ! -x "$UVICORN_BIN" ]]; then
  UVICORN_BIN="uvicorn"
fi

PORT="${PORT:-0}"
if [[ "$PORT" == "0" ]]; then
  PORT="$("$PY_BIN" - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT}}"

TENANT_ID="${TENANT_ID:-tenant-1}"
ORG_ID="${ORG_ID:-org-1}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_baseline_filters_${timestamp}.db}"
db_path_norm="${DB_PATH#/}"

STORAGE_DIR="${STORAGE_DIR:-${OUT_DIR}/storage}"
mkdir -p "$STORAGE_DIR"

export PYTHONPATH="${PYTHONPATH:-src}"

# Force an isolated ephemeral DB for this verification, even if the caller has
# YUANTUS_* env vars set (e.g., running via scripts/verify_all.sh).
export YUANTUS_TENANCY_MODE="single"
export YUANTUS_SCHEMA_MODE="create_all"
export YUANTUS_STORAGE_TYPE="local"
export YUANTUS_LOCAL_STORAGE_PATH="$STORAGE_DIR"
export YUANTUS_DATABASE_URL="sqlite:////${db_path_norm}"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:////${db_path_norm}"

# Ensure auth is enforced.
export YUANTUS_AUTH_MODE="required"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

log "Seed identity/meta (db=${DB_PATH})"
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
  --user-id 1 --roles admin >/dev/null
"$YUANTUS_BIN" seed-meta >/dev/null

server_log="${OUT_DIR}/server.log"
log "Start API server (base=${BASE_URL})"
"$UVICORN_BIN" yuantus.api.app:app --host 127.0.0.1 --port "$PORT" >"$server_log" 2>&1 &
server_pid="$!"

cleanup() {
  kill "$server_pid" >/dev/null 2>&1 || true
  rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true
}
trap cleanup EXIT

log "Wait for /health"
for _ in {1..60}; do
  if curl -fsS "${BASE_URL}/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "${BASE_URL}/api/v1/health" >"${OUT_DIR}/health.json" || fail "health failed (see ${server_log})"

json_get() {
  "$PY_BIN" - "$1" "$2" <<'PY'
import json
import sys

path = sys.argv[2].split(".")
with open(sys.argv[1], "r", encoding="utf-8") as f:
  cur = json.load(f)
for key in path:
  if isinstance(cur, dict):
    cur = cur.get(key)
  else:
    cur = None
    break
print("" if cur is None else str(cur))
PY
}

assert_eq() {
  local label="$1"
  local got="$2"
  local want="$3"
  if [[ "$got" != "$want" ]]; then
    fail "${label}: expected '${want}', got '${got}'"
  fi
}

assert_nonempty() {
  local label="$1"
  local val="$2"
  if [[ -z "$val" ]]; then
    fail "${label}: expected non-empty"
  fi
}

log "Login (admin)"
login_json="${OUT_DIR}/login_admin.json"
code="$(
  curl -sS -o "$login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_json" >&2 || true
  fail "admin login -> HTTP $code"
fi
ADMIN_TOKEN="$("$PY_BIN" - "$login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "admin.access_token" "$ADMIN_TOKEN"

admin_header=(-H "Authorization: Bearer ${ADMIN_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")

ts="$(date +%s)"
effective_date="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
effective_from="$(date -u -v-1d +"%Y-%m-%dT%H:%M:%SZ")"
effective_to="$(date -u -v+1d +"%Y-%m-%dT%H:%M:%SZ")"

log "Create Part (baseline root)"
part_json="${OUT_DIR}/part_create.json"
code="$(
  curl -sS -o "$part_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-FILTER-${ts}\",\"name\":\"Baseline Filter Test\"}}"
)"
assert_eq "create part http_code" "$code" "200"
PART_ID="$(json_get "$part_json" id)"
assert_nonempty "part.id" "$PART_ID"

log "Create baseline with explicit baseline_type/scope/state/effective_date"
baseline_json="${OUT_DIR}/baseline_create.json"
code="$(
  curl -sS -o "$baseline_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/baselines" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"BL Filter Test ${ts}\",\"root_item_id\":\"${PART_ID}\",\"baseline_type\":\"design\",\"scope\":\"product\",\"state\":\"released\",\"effective_date\":\"${effective_date}\",\"include_documents\":false,\"include_relationships\":false}"
)"
assert_eq "baseline create http_code" "$code" "200"
BASELINE_ID="$(json_get "$baseline_json" id)"
assert_nonempty "baseline.id" "$BASELINE_ID"

log "List baselines filtered by type/scope/state (expect all returned rows match)"
list_json="${OUT_DIR}/baselines_list_type_scope_state.json"
code="$(
  curl -sS -o "$list_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/baselines?baseline_type=design&scope=product&state=released&limit=50&offset=0" \
    "${admin_header[@]}"
)"
assert_eq "baselines list (type/scope/state) http_code" "$code" "200"
"$PY_BIN" - "$list_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
items = resp.get("items") or []
for item in items:
  if item.get("baseline_type") != "design":
    raise SystemExit("baseline_type mismatch")
  if item.get("scope") != "product":
    raise SystemExit("scope mismatch")
  if item.get("state") != "released":
    raise SystemExit("state mismatch")
print("baseline_filters_type_scope_state_ok=1")
PY

log "List baselines filtered by effective_date range (expect returned rows in range)"
range_json="${OUT_DIR}/baselines_list_effective_range.json"
code="$(
  curl -sS -o "$range_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/baselines?effective_from=${effective_from}&effective_to=${effective_to}&limit=50&offset=0" \
    "${admin_header[@]}"
)"
assert_eq "baselines list (effective range) http_code" "$code" "200"
"$PY_BIN" - "$range_json" "$effective_from" "$effective_to" <<'PY'
import json
import sys
from datetime import datetime, timezone

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
start_raw, end_raw = sys.argv[2], sys.argv[3]

def parse_iso(dt: str) -> datetime:
  if dt.endswith("Z"):
    dt = dt[:-1] + "+00:00"
  return datetime.fromisoformat(dt).astimezone(timezone.utc)

start = parse_iso(start_raw)
end = parse_iso(end_raw)
items = resp.get("items") or []
for item in items:
  raw = item.get("effective_date") or ""
  if not raw:
    raise SystemExit("missing effective_date")
  val = parse_iso(raw)
  if val < start or val > end:
    raise SystemExit("effective_date out of range")
print("baseline_filters_effective_range_ok=1")
PY

log "PASS: Baseline Filters API E2E verification"

