#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for BOM effectivity (date-based).
#
# Coverage:
# - BOM lines with effectivity_from/to are correctly filtered by date
# - Same BOM tree returns different children at different dates
# - RBAC: viewer cannot add BOM children (403) but can read effective BOM (200)
# - DELETE BOM relationship removes it from future effective queries (cascade behavior)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-bom-effectivity/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_bom_effectivity_${timestamp}.db}"
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
  --user-id 1 --roles admin --superuser >/dev/null
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

log "Compute date context (UTC ISO strings)"
date_ctx_json="${OUT_DIR}/date_ctx.json"
"$PY_BIN" - "$date_ctx_json" <<'PY'
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

now = datetime.now(tz=timezone.utc)
def fmt(dt: datetime) -> str:
  # Drop microseconds to keep URLs shorter and comparable.
  dt = dt.replace(microsecond=0)
  return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

ctx = {
  "today": fmt(now),
  "next_week": fmt(now + timedelta(days=7)),
  "last_week": fmt(now - timedelta(days=7)),
  "two_weeks_ago": fmt(now - timedelta(days=14)),
}
Path(sys.argv[1]).write_text(json.dumps(ctx, indent=2) + "\n", encoding="utf-8")
print(json.dumps(ctx))
PY

TODAY="$(json_get "$date_ctx_json" today)"
NEXT_WEEK="$(json_get "$date_ctx_json" next_week)"
LAST_WEEK="$(json_get "$date_ctx_json" last_week)"
TWO_WEEKS_AGO="$(json_get "$date_ctx_json" two_weeks_ago)"

assert_nonempty "TODAY" "$TODAY"
assert_nonempty "NEXT_WEEK" "$NEXT_WEEK"
assert_nonempty "LAST_WEEK" "$LAST_WEEK"
assert_nonempty "TWO_WEEKS_AGO" "$TWO_WEEKS_AGO"

ts="$(date +%s)"
VIEWER_USER="viewer-${ts}"
VIEWER_ID="$("$PY_BIN" - <<PY
print(10000 + (${ts} % 100000))
PY
)"

log "Seed viewer identity (no-superuser)"
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$VIEWER_USER" --password viewer \
  --user-id "$VIEWER_ID" --roles viewer --no-superuser >/dev/null

log "Configure PermissionSets for read-only viewer"
perm_id="EffReadOnly-${ts}"
perm_create_json="${OUT_DIR}/permission_create.json"
code="$(
  curl -sS -o "$perm_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/meta/permissions" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"id\":\"${perm_id}\",\"name\":\"Effectivity Read Only\"}"
)"
assert_eq "meta permission create http_code" "$code" "200"

perm_access_viewer_json="${OUT_DIR}/permission_access_viewer.json"
code="$(
  curl -sS -o "$perm_access_viewer_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/meta/permissions/${perm_id}/accesses" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"identity_id":"viewer","can_create":false,"can_get":true,"can_update":false,"can_delete":false,"can_discover":true}'
)"
assert_eq "meta permission add access (viewer) http_code" "$code" "200"

perm_access_admin_json="${OUT_DIR}/permission_access_admin.json"
code="$(
  curl -sS -o "$perm_access_admin_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/meta/permissions/${perm_id}/accesses" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"identity_id":"admin","can_create":true,"can_get":true,"can_update":true,"can_delete":true,"can_discover":true}'
)"
assert_eq "meta permission add access (admin) http_code" "$code" "200"

perm_patch_part_json="${OUT_DIR}/permission_patch_part.json"
code="$(
  curl -sS -o "$perm_patch_part_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/meta/item-types/Part/permission" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"permission_id\":\"${perm_id}\"}"
)"
assert_eq "meta item-type Part permission patch http_code" "$code" "200"

perm_patch_bom_json="${OUT_DIR}/permission_patch_part_bom.json"
code="$(
  curl -sS -o "$perm_patch_bom_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/meta/item-types/Part%20BOM/permission" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"permission_id\":\"${perm_id}\"}"
)"
assert_eq "meta item-type Part BOM permission patch http_code" "$code" "200"

log "Create test parts (A parent; B future; C current; D expired)"
part_a_json="${OUT_DIR}/part_a_create.json"
code="$(
  curl -sS -o "$part_a_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"P-EFF-A-${ts}\",\"name\":\"Effectivity Parent\"}}"
)"
assert_eq "create part A http_code" "$code" "200"
PART_A_ID="$(json_get "$part_a_json" id)"
assert_nonempty "part_a.id" "$PART_A_ID"

part_b_json="${OUT_DIR}/part_b_create.json"
code="$(
  curl -sS -o "$part_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"P-EFF-B-${ts}\",\"name\":\"Future Child (next week)\"}}"
)"
assert_eq "create part B http_code" "$code" "200"
PART_B_ID="$(json_get "$part_b_json" id)"
assert_nonempty "part_b.id" "$PART_B_ID"

part_c_json="${OUT_DIR}/part_c_create.json"
code="$(
  curl -sS -o "$part_c_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"P-EFF-C-${ts}\",\"name\":\"Current Child (now)\"}}"
)"
assert_eq "create part C http_code" "$code" "200"
PART_C_ID="$(json_get "$part_c_json" id)"
assert_nonempty "part_c.id" "$PART_C_ID"

part_d_json="${OUT_DIR}/part_d_create.json"
code="$(
  curl -sS -o "$part_d_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"P-EFF-D-${ts}\",\"name\":\"Expired Child (last week)\"}}"
)"
assert_eq "create part D http_code" "$code" "200"
PART_D_ID="$(json_get "$part_d_json" id)"
assert_nonempty "part_d.id" "$PART_D_ID"

log "Build BOM with effectivity dates"
rel_ab_json="${OUT_DIR}/rel_a_b_add.json"
code="$(
  curl -sS -o "$rel_ab_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_A_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_B_ID}\",\"quantity\":1,\"effectivity_from\":\"${NEXT_WEEK}\"}"
)"
assert_eq "add A->B http_code" "$code" "200"
assert_eq "add A->B ok" "$(json_get "$rel_ab_json" ok)" "True"

rel_ac_json="${OUT_DIR}/rel_a_c_add.json"
code="$(
  curl -sS -o "$rel_ac_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_A_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_C_ID}\",\"quantity\":2,\"effectivity_from\":\"${LAST_WEEK}\"}"
)"
assert_eq "add A->C http_code" "$code" "200"
assert_eq "add A->C ok" "$(json_get "$rel_ac_json" ok)" "True"

rel_ad_json="${OUT_DIR}/rel_a_d_add.json"
code="$(
  curl -sS -o "$rel_ad_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_A_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_D_ID}\",\"quantity\":1,\"effectivity_from\":\"${TWO_WEEKS_AGO}\",\"effectivity_to\":\"${LAST_WEEK}\"}"
)"
assert_eq "add A->D http_code" "$code" "200"
assert_eq "add A->D ok" "$(json_get "$rel_ad_json" ok)" "True"

assert_children_set() {
  local json_file="$1"
  local want_csv="$2"
  "$PY_BIN" - "$json_file" "$want_csv" <<'PY'
import json
import sys

want = sorted([x for x in sys.argv[2].split(",") if x])
with open(sys.argv[1], "r", encoding="utf-8") as f:
  tree = json.load(f)
children = tree.get("children") or []
got = []
for c in children:
  child = (c or {}).get("child") or {}
  if child.get("id"):
    got.append(str(child["id"]))
got = sorted(got)
if got != want:
  raise SystemExit(f"expected children={want}, got={got}")
print("children_set_ok=1")
PY
}

log "Query effective BOM at TODAY (expect only C)"
eff_today_json="${OUT_DIR}/effective_today.json"
code="$(
  curl -sS -o "$eff_today_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PART_A_ID}/effective?date=${TODAY}" \
    "${admin_header[@]}"
)"
assert_eq "effective(today) http_code" "$code" "200"
assert_children_set "$eff_today_json" "$PART_C_ID"

log "Query effective BOM at NEXT_WEEK (expect B + C)"
eff_next_json="${OUT_DIR}/effective_next_week.json"
code="$(
  curl -sS -o "$eff_next_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PART_A_ID}/effective?date=${NEXT_WEEK}" \
    "${admin_header[@]}"
)"
assert_eq "effective(next_week) http_code" "$code" "200"
assert_children_set "$eff_next_json" "${PART_B_ID},${PART_C_ID}"

log "Query effective BOM at LAST_WEEK (expect C + D)"
eff_last_json="${OUT_DIR}/effective_last_week.json"
code="$(
  curl -sS -o "$eff_last_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PART_A_ID}/effective?date=${LAST_WEEK}" \
    "${admin_header[@]}"
)"
assert_eq "effective(last_week) http_code" "$code" "200"
assert_children_set "$eff_last_json" "${PART_C_ID},${PART_D_ID}"

log "Viewer login"
viewer_login_json="${OUT_DIR}/login_viewer.json"
code="$(
  curl -sS -o "$viewer_login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${VIEWER_USER}\",\"password\":\"viewer\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$viewer_login_json" >&2 || true
  fail "viewer login -> HTTP $code"
fi
VIEWER_TOKEN="$("$PY_BIN" - "$viewer_login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "viewer.access_token" "$VIEWER_TOKEN"

viewer_header=(-H "Authorization: Bearer ${VIEWER_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")

log "RBAC: viewer cannot add BOM child (expect 403)"
part_e_json="${OUT_DIR}/part_e_create.json"
code="$(
  curl -sS -o "$part_e_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"P-EFF-E-${ts}\",\"name\":\"Viewer Test Part\"}}"
)"
assert_eq "create part E http_code" "$code" "200"
PART_E_ID="$(json_get "$part_e_json" id)"
assert_nonempty "part_e.id" "$PART_E_ID"

viewer_bom_add_json="${OUT_DIR}/viewer_bom_add_attempt.json"
code="$(
  curl -sS -o "$viewer_bom_add_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_A_ID}/children" \
    "${viewer_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_E_ID}\",\"quantity\":1}"
)"
assert_eq "viewer add bom child http_code" "$code" "403"

log "RBAC: viewer can read effective BOM (expect 200)"
viewer_eff_json="${OUT_DIR}/viewer_effective_read.json"
code="$(
  curl -sS -o "$viewer_eff_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PART_A_ID}/effective" \
    "${viewer_header[@]}"
)"
assert_eq "viewer read effective bom http_code" "$code" "200"

log "Delete BOM relationship A->B (expect 200)"
delete_ab_json="${OUT_DIR}/delete_a_b.json"
code="$(
  curl -sS -o "$delete_ab_json" -w "%{http_code}" \
    -X DELETE "${BASE_URL}/api/v1/bom/${PART_A_ID}/children/${PART_B_ID}" \
    "${admin_header[@]}"
)"
assert_eq "delete A->B http_code" "$code" "200"

log "After delete, NEXT_WEEK should show only C"
eff_after_delete_json="${OUT_DIR}/effective_next_week_after_delete.json"
code="$(
  curl -sS -o "$eff_after_delete_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PART_A_ID}/effective?date=${NEXT_WEEK}" \
    "${admin_header[@]}"
)"
assert_eq "effective(next_week, after delete) http_code" "$code" "200"
assert_children_set "$eff_after_delete_json" "$PART_C_ID"

log "PASS: BOM effectivity (date-based) API E2E verification"

