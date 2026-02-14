#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for BOM tree operations + cycle detection.
#
# Coverage:
# - add child: POST /api/v1/bom/{parent_id}/children
# - remove child: DELETE /api/v1/bom/{parent_id}/children/{child_id}
# - tree query: GET /api/v1/bom/{parent_id}/tree?depth=...
# - cycle detection returns 409 with cycle path payload
# - duplicate add prevention returns 400
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-bom-tree/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_bom_tree_${timestamp}.db}"
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

ts="$(date +%s)"

create_part() {
  local out="$1"
  local number="$2"
  local name="$3"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/aml/apply" \
      "${admin_header[@]}" -H 'content-type: application/json' \
      -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${number}\",\"name\":\"${name}\"}}"
  )"
  [[ "$http_code" == "200" ]] || fail "create part ${number} -> HTTP ${http_code} (out=${out})"
  json_get "$out" id
}

log "Create test parts (A,B,C,D)"
PART_A_ID="$(create_part "${OUT_DIR}/part_a.json" "P-BOM-A-${ts}" "Part A (Top)")"
PART_B_ID="$(create_part "${OUT_DIR}/part_b.json" "P-BOM-B-${ts}" "Part B (Level 2)")"
PART_C_ID="$(create_part "${OUT_DIR}/part_c.json" "P-BOM-C-${ts}" "Part C (Level 3)")"
PART_D_ID="$(create_part "${OUT_DIR}/part_d.json" "P-BOM-D-${ts}" "Part D (Level 3 sibling)")"
assert_nonempty "part_a.id" "$PART_A_ID"
assert_nonempty "part_b.id" "$PART_B_ID"
assert_nonempty "part_c.id" "$PART_C_ID"
assert_nonempty "part_d.id" "$PART_D_ID"

log "Build BOM: A -> B; B -> C; B -> D"
rel_ab_json="${OUT_DIR}/rel_a_b.json"
code="$(
  curl -sS -o "$rel_ab_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_A_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_B_ID}\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"10\"}"
)"
assert_eq "add A->B http_code" "$code" "200"
assert_eq "add A->B ok" "$(json_get "$rel_ab_json" ok)" "True"
assert_nonempty "A->B relationship_id" "$(json_get "$rel_ab_json" relationship_id)"

rel_bc_json="${OUT_DIR}/rel_b_c.json"
code="$(
  curl -sS -o "$rel_bc_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_B_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_C_ID}\",\"quantity\":3,\"uom\":\"KG\",\"find_num\":\"20\"}"
)"
assert_eq "add B->C http_code" "$code" "200"
assert_eq "add B->C ok" "$(json_get "$rel_bc_json" ok)" "True"
assert_nonempty "B->C relationship_id" "$(json_get "$rel_bc_json" relationship_id)"

rel_bd_json="${OUT_DIR}/rel_b_d.json"
code="$(
  curl -sS -o "$rel_bd_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_B_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_D_ID}\",\"quantity\":1,\"uom\":\"EA\",\"find_num\":\"30\"}"
)"
assert_eq "add B->D http_code" "$code" "200"
assert_eq "add B->D ok" "$(json_get "$rel_bd_json" ok)" "True"
assert_nonempty "B->D relationship_id" "$(json_get "$rel_bd_json" relationship_id)"

assert_tree_topology() {
  local json_file="$1"
  local want_b="$2"
  local want_child_csv="$3"
  "$PY_BIN" - "$json_file" "$want_b" "$want_child_csv" <<'PY'
import json
import sys

want_b = sys.argv[2]
want_children = sorted([x for x in sys.argv[3].split(",") if x])

with open(sys.argv[1], "r", encoding="utf-8") as f:
  tree = json.load(f)
children = tree.get("children") or []
if len(children) != 1:
  raise SystemExit(f"expected level1 children=1, got {len(children)}")

lvl1_child = (children[0] or {}).get("child") or {}
lvl1_id = str(lvl1_child.get("id") or "")
if lvl1_id != want_b:
  raise SystemExit(f"expected level1 child id={want_b}, got {lvl1_id}")

lvl2 = lvl1_child.get("children") or []
got = []
for c in lvl2:
  cid = str(((c or {}).get("child") or {}).get("id") or "")
  if cid:
    got.append(cid)
got = sorted(got)
if got != want_children:
  raise SystemExit(f"expected level2 children={want_children}, got={got}")

print("bom_tree_topology_ok=1")
PY
}

log "Tree depth=10 (expect A->B and B->{C,D})"
tree_full_json="${OUT_DIR}/tree_full.json"
code="$(
  curl -sS -o "$tree_full_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PART_A_ID}/tree?depth=10" \
    "${admin_header[@]}"
)"
assert_eq "tree full http_code" "$code" "200"
assert_tree_topology "$tree_full_json" "$PART_B_ID" "${PART_C_ID},${PART_D_ID}"

log "Tree depth=1 (expect A->B only; B has no children)"
tree_l1_json="${OUT_DIR}/tree_depth1.json"
code="$(
  curl -sS -o "$tree_l1_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PART_A_ID}/tree?depth=1" \
    "${admin_header[@]}"
)"
assert_eq "tree depth=1 http_code" "$code" "200"
assert_tree_topology "$tree_l1_json" "$PART_B_ID" ""

log "Cycle detection: C -> A should return 409"
cycle_json="${OUT_DIR}/cycle_response.json"
code="$(
  curl -sS -o "$cycle_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_C_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_A_ID}\",\"quantity\":1}"
)"
assert_eq "cycle C->A http_code" "$code" "409"
"$PY_BIN" - "$cycle_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
if (resp.get("error") or "") != "CYCLE_DETECTED":
  raise SystemExit(f"expected error=CYCLE_DETECTED, got {resp.get('error')}")
path = resp.get("cycle_path") or []
if not isinstance(path, list) or len(path) == 0:
  raise SystemExit(f"expected non-empty cycle_path, got {path!r}")
print("cycle_detect_ok=1")
PY

log "Self-reference: A -> A should return 409"
self_cycle_json="${OUT_DIR}/self_cycle_response.json"
code="$(
  curl -sS -o "$self_cycle_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_A_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_A_ID}\",\"quantity\":1}"
)"
assert_eq "self cycle A->A http_code" "$code" "409"

log "Duplicate add: A -> B again should return 400"
dup_json="${OUT_DIR}/duplicate_add_response.json"
code="$(
  curl -sS -o "$dup_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PART_A_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PART_B_ID}\",\"quantity\":1}"
)"
assert_eq "duplicate add A->B http_code" "$code" "400"

log "Remove child: B -> D should return 200"
rm_json="${OUT_DIR}/remove_b_d.json"
code="$(
  curl -sS -o "$rm_json" -w "%{http_code}" \
    -X DELETE "${BASE_URL}/api/v1/bom/${PART_B_ID}/children/${PART_D_ID}" \
    "${admin_header[@]}"
)"
assert_eq "delete B->D http_code" "$code" "200"

log "After delete, tree depth=10 should have only C under B"
tree_after_json="${OUT_DIR}/tree_after_delete.json"
code="$(
  curl -sS -o "$tree_after_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PART_A_ID}/tree?depth=10" \
    "${admin_header[@]}"
)"
assert_eq "tree after delete http_code" "$code" "200"
assert_tree_topology "$tree_after_json" "$PART_B_ID" "$PART_C_ID"

log "Remove non-existent relationship: A -> D should return 404"
rm_404_json="${OUT_DIR}/remove_nonexistent.json"
code="$(
  curl -sS -o "$rm_404_json" -w "%{http_code}" \
    -X DELETE "${BASE_URL}/api/v1/bom/${PART_A_ID}/children/${PART_D_ID}" \
    "${admin_header[@]}"
)"
assert_eq "delete A->D(non-existent) http_code" "$code" "404"

log "PASS: BOM tree + cycle detection API E2E verification"

