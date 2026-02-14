#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Versions core semantics.
#
# Coverage:
# - init/revise/tree/history
# - checkout/checkin + lock contention (2nd user blocked)
# - revision utilities: next/parse/compare
# - iterations: create/latest
# - compare versions (property diffs)
# - revision scheme: create/list
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-versions/${timestamp}"
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
VIEWER_USERNAME="${VIEWER_USERNAME:-viewer}"
VIEWER_PASSWORD="${VIEWER_PASSWORD:-viewer}"

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_versions_${timestamp}.db}"
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

# Ensure auth is enforced (avoid get_current_user_id_optional defaulting to user_id=1).
export YUANTUS_AUTH_MODE="required"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

log "Seed identity/meta (db=${DB_PATH})"
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
  --user-id 1 --roles admin --superuser >/dev/null
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$VIEWER_USERNAME" --password "$VIEWER_PASSWORD" \
  --user-id 2 --roles viewer --no-superuser >/dev/null
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
login_admin_json="${OUT_DIR}/login_admin.json"
code="$(
  curl -sS -o "$login_admin_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_admin_json" >&2 || true
  fail "admin login -> HTTP $code"
fi
ADMIN_TOKEN="$("$PY_BIN" - "$login_admin_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "admin.access_token" "$ADMIN_TOKEN"

log "Login (viewer)"
login_viewer_json="${OUT_DIR}/login_viewer.json"
code="$(
  curl -sS -o "$login_viewer_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${VIEWER_USERNAME}\",\"password\":\"${VIEWER_PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_viewer_json" >&2 || true
  fail "viewer login -> HTTP $code"
fi
VIEWER_TOKEN="$("$PY_BIN" - "$login_viewer_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "viewer.access_token" "$VIEWER_TOKEN"

admin_header=(-H "Authorization: Bearer ${ADMIN_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")
viewer_header=(-H "Authorization: Bearer ${VIEWER_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")

ts="$(date +%s)"

log "Create Part (versionable)"
part_json="${OUT_DIR}/part_create.json"
code="$(
  curl -sS -o "$part_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"P-VER-${ts}\",\"name\":\"Versions E2E\"}}"
)"
assert_eq "create part http_code" "$code" "200"
ITEM_ID="$(json_get "$part_json" id)"
assert_nonempty "part.id" "$ITEM_ID"

log "Init version (expect 1.A)"
ver_init_json="${OUT_DIR}/version_init.json"
code="$(
  curl -sS -o "$ver_init_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/init" \
    "${admin_header[@]}"
)"
assert_eq "init version http_code" "$code" "200"
VER_A_ID="$(json_get "$ver_init_json" id)"
VER_A_LABEL="$(json_get "$ver_init_json" version_label)"
assert_nonempty "version.id" "$VER_A_ID"
assert_eq "version_label" "$VER_A_LABEL" "1.A"

log "Checkout as admin (lock version)"
checkout_admin_json="${OUT_DIR}/checkout_admin.json"
code="$(
  curl -sS -o "$checkout_admin_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/checkout" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"lock for edit\"}"
)"
assert_eq "checkout admin http_code" "$code" "200"
assert_eq "checkout.checked_out_by_id" "$(json_get "$checkout_admin_json" checked_out_by_id)" "1"

log "Checkout as viewer should be blocked (400)"
checkout_viewer_json="${OUT_DIR}/checkout_viewer_blocked.json"
code="$(
  curl -sS -o "$checkout_viewer_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/checkout" \
    "${viewer_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"try lock\"}"
)"
assert_eq "checkout viewer blocked http_code" "$code" "400"

log "Checkin with property update (unlock)"
checkin_a_json="${OUT_DIR}/checkin_a.json"
code="$(
  curl -sS -o "$checkin_a_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/checkin" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"edit done\",\"properties\":{\"description\":\"Updated via checkin\"}}"
)"
assert_eq "checkin http_code" "$code" "200"
assert_eq "checkin.checked_out_by_id" "$(json_get "$checkin_a_json" checked_out_by_id)" ""

log "Revise (1.A -> 1.B)"
revise_b_json="${OUT_DIR}/revise_b.json"
code="$(
  curl -sS -o "$revise_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/revise" \
    "${admin_header[@]}"
)"
assert_eq "revise B http_code" "$code" "200"
VER_B_ID="$(json_get "$revise_b_json" id)"
VER_B_LABEL="$(json_get "$revise_b_json" version_label)"
assert_nonempty "version_b.id" "$VER_B_ID"
assert_eq "version_b.label" "$VER_B_LABEL" "1.B"

log "Checkout 1.B then checkin with property update (create diff)"
checkout_b_json="${OUT_DIR}/checkout_b.json"
code="$(
  curl -sS -o "$checkout_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/checkout" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"edit B\"}"
)"
assert_eq "checkout B http_code" "$code" "200"

checkin_b_json="${OUT_DIR}/checkin_b.json"
code="$(
  curl -sS -o "$checkin_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/checkin" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"edit B done\",\"properties\":{\"description\":\"Updated in B\"}}"
)"
assert_eq "checkin B http_code" "$code" "200"

log "Compare versions (1.A vs 1.B) includes description diff"
compare_json="${OUT_DIR}/compare_a_b.json"
code="$(
  curl -sS -o "$compare_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/compare?v1=${VER_A_ID}&v2=${VER_B_ID}" \
    "${admin_header[@]}"
)"
assert_eq "compare A vs B http_code" "$code" "200"
"$PY_BIN" - "$compare_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)

if data.get("version_a") != "1.A" or data.get("version_b") != "1.B":
  raise SystemExit(f"unexpected compare labels: {data.get('version_a')} vs {data.get('version_b')}")

diffs = data.get("diffs") or {}
desc = diffs.get("description") or {}
if desc.get("a") != "Updated via checkin" or desc.get("b") != "Updated in B":
  raise SystemExit(f"unexpected description diff: {desc}")
print("compare_ok=1")
PY

log "Revise again (1.B -> 1.C)"
revise_c_json="${OUT_DIR}/revise_c.json"
code="$(
  curl -sS -o "$revise_c_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/revise" \
    "${admin_header[@]}"
)"
assert_eq "revise C http_code" "$code" "200"
VER_C_ID="$(json_get "$revise_c_json" id)"
VER_C_LABEL="$(json_get "$revise_c_json" version_label)"
assert_nonempty "version_c.id" "$VER_C_ID"
assert_eq "version_c.label" "$VER_C_LABEL" "1.C"

log "Version tree contains 1.A,1.B,1.C"
tree_json="${OUT_DIR}/tree.json"
code="$(
  curl -sS -o "$tree_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/tree" \
    "${admin_header[@]}"
)"
assert_eq "tree http_code" "$code" "200"
"$PY_BIN" - "$tree_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or []
labels = sorted([x.get("label") for x in data if x and x.get("label")])
want = ["1.A", "1.B", "1.C"]
if labels != want:
  raise SystemExit(f"expected labels={want}, got={labels}")
print("tree_ok=1")
PY

log "History has expected minimum entries"
hist_json="${OUT_DIR}/history.json"
code="$(
  curl -sS -o "$hist_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/history" \
    "${admin_header[@]}"
)"
assert_eq "history http_code" "$code" "200"
"$PY_BIN" - "$hist_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or []
if len(data) < 5:
  raise SystemExit(f"expected history entries >= 5, got {len(data)}")
print("history_ok=1")
PY

log "Revision next: letter A->B, Z->AA; number 1->2; hybrid A99->B1"
rev_next_a_json="${OUT_DIR}/rev_next_letter_a.json"
code="$(
  curl -sS -o "$rev_next_a_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/revision/next?current=A&scheme=letter" \
    "${admin_header[@]}"
)"
assert_eq "rev_next A http_code" "$code" "200"
assert_eq "rev_next(A)" "$(json_get "$rev_next_a_json" next)" "B"

rev_next_z_json="${OUT_DIR}/rev_next_letter_z.json"
code="$(
  curl -sS -o "$rev_next_z_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/revision/next?current=Z&scheme=letter" \
    "${admin_header[@]}"
)"
assert_eq "rev_next Z http_code" "$code" "200"
assert_eq "rev_next(Z)" "$(json_get "$rev_next_z_json" next)" "AA"

rev_next_num_json="${OUT_DIR}/rev_next_number_1.json"
code="$(
  curl -sS -o "$rev_next_num_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/revision/next?current=1&scheme=number" \
    "${admin_header[@]}"
)"
assert_eq "rev_next 1 http_code" "$code" "200"
assert_eq "rev_next(1)" "$(json_get "$rev_next_num_json" next)" "2"

rev_next_hybrid_json="${OUT_DIR}/rev_next_hybrid_a99.json"
code="$(
  curl -sS -o "$rev_next_hybrid_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/revision/next?current=A99&scheme=hybrid" \
    "${admin_header[@]}"
)"
assert_eq "rev_next A99 http_code" "$code" "200"
assert_eq "rev_next(A99)" "$(json_get "$rev_next_hybrid_json" next)" "B1"

log "Revision parse: AA -> letter value=27"
rev_parse_json="${OUT_DIR}/rev_parse_aa.json"
code="$(
  curl -sS -o "$rev_parse_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/revision/parse?revision=AA" \
    "${admin_header[@]}"
)"
assert_eq "rev_parse AA http_code" "$code" "200"
assert_eq "rev_parse.scheme" "$(json_get "$rev_parse_json" scheme)" "letter"
assert_eq "rev_parse.value" "$(json_get "$rev_parse_json" value)" "27"

log "Revision compare: A < C"
rev_cmp_json="${OUT_DIR}/rev_compare_a_c.json"
code="$(
  curl -sS -o "$rev_cmp_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/revision/compare?rev_a=A&rev_b=C" \
    "${admin_header[@]}"
)"
assert_eq "rev_compare http_code" "$code" "200"
assert_eq "rev_compare.comparison" "$(json_get "$rev_cmp_json" comparison)" "-1"

log "Create iterations (1.C.1, 1.C.2) and verify latest"
iter1_json="${OUT_DIR}/iteration_1.json"
code="$(
  curl -sS -o "$iter1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/${VER_C_ID}/iterations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"description\":\"First iteration\",\"source_type\":\"manual\"}"
)"
assert_eq "create iteration1 http_code" "$code" "200"
assert_eq "iteration1.number" "$(json_get "$iter1_json" iteration_number)" "1"
assert_eq "iteration1.label" "$(json_get "$iter1_json" iteration_label)" "1.C.1"

iter2_json="${OUT_DIR}/iteration_2.json"
code="$(
  curl -sS -o "$iter2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/${VER_C_ID}/iterations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"description\":\"Second iteration\",\"source_type\":\"auto_save\"}"
)"
assert_eq "create iteration2 http_code" "$code" "200"
assert_eq "iteration2.number" "$(json_get "$iter2_json" iteration_number)" "2"
assert_eq "iteration2.label" "$(json_get "$iter2_json" iteration_label)" "1.C.2"

iter_latest_json="${OUT_DIR}/iteration_latest.json"
code="$(
  curl -sS -o "$iter_latest_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/${VER_C_ID}/iterations/latest" \
    "${admin_header[@]}"
)"
assert_eq "latest iteration http_code" "$code" "200"
assert_eq "latest iteration label" "$(json_get "$iter_latest_json" iteration_label)" "1.C.2"

log "Create revision scheme (number) and list schemes"
scheme_create_json="${OUT_DIR}/scheme_create.json"
code="$(
  curl -sS -o "$scheme_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/schemes" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"TestScheme-${ts}\",\"scheme_type\":\"number\",\"initial_revision\":\"1\",\"is_default\":false}"
)"
assert_eq "scheme create http_code" "$code" "200"
assert_eq "scheme.scheme_type" "$(json_get "$scheme_create_json" scheme_type)" "number"
assert_eq "scheme.initial_revision" "$(json_get "$scheme_create_json" initial_revision)" "1"

scheme_list_json="${OUT_DIR}/scheme_list.json"
code="$(
  curl -sS -o "$scheme_list_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/schemes" \
    "${admin_header[@]}"
)"
assert_eq "scheme list http_code" "$code" "200"
"$PY_BIN" - "$scheme_list_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or []
if len(data) < 1:
  raise SystemExit("expected at least one scheme")
print("schemes_ok=1")
PY

log "PASS: Versions core E2E verification"

