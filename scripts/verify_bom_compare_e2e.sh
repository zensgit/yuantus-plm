#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for BOM Compare.
#
# Coverage:
# - build two parent BOMs with add/remove/change + effectivity + substitutes
# - compare output summary + changed fields contract
# - compare_mode variants: only_product, num_qty, summarized
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-bom-compare/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_bom_compare_${timestamp}.db}"
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
effective_from="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

log "Create parents A/B and children X/Y/Z + substitute"
parent_a_json="${OUT_DIR}/parent_a_create.json"
code="$(
  curl -sS -o "$parent_a_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-A-${ts}\",\"name\":\"Compare A\"}}"
)"
assert_eq "create parent A http_code" "$code" "200"
PARENT_A_ID="$(json_get "$parent_a_json" id)"
assert_nonempty "parent_a.id" "$PARENT_A_ID"

parent_b_json="${OUT_DIR}/parent_b_create.json"
code="$(
  curl -sS -o "$parent_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-B-${ts}\",\"name\":\"Compare B\"}}"
)"
assert_eq "create parent B http_code" "$code" "200"
PARENT_B_ID="$(json_get "$parent_b_json" id)"
assert_nonempty "parent_b.id" "$PARENT_B_ID"

child_x_json="${OUT_DIR}/child_x_create.json"
code="$(
  curl -sS -o "$child_x_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-X-${ts}\",\"name\":\"Child X\"}}"
)"
assert_eq "create child X http_code" "$code" "200"
CHILD_X_ID="$(json_get "$child_x_json" id)"
assert_nonempty "child_x.id" "$CHILD_X_ID"

child_y_json="${OUT_DIR}/child_y_create.json"
code="$(
  curl -sS -o "$child_y_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-Y-${ts}\",\"name\":\"Child Y\"}}"
)"
assert_eq "create child Y http_code" "$code" "200"
CHILD_Y_ID="$(json_get "$child_y_json" id)"
assert_nonempty "child_y.id" "$CHILD_Y_ID"

child_z_json="${OUT_DIR}/child_z_create.json"
code="$(
  curl -sS -o "$child_z_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-Z-${ts}\",\"name\":\"Child Z\"}}"
)"
assert_eq "create child Z http_code" "$code" "200"
CHILD_Z_ID="$(json_get "$child_z_json" id)"
assert_nonempty "child_z.id" "$CHILD_Z_ID"

sub_part_json="${OUT_DIR}/sub_part_create.json"
code="$(
  curl -sS -o "$sub_part_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-S-${ts}\",\"name\":\"Substitute ${ts}\"}}"
)"
assert_eq "create substitute http_code" "$code" "200"
SUB_PART_ID="$(json_get "$sub_part_json" id)"
assert_nonempty "sub_part.id" "$SUB_PART_ID"

log "Build BOM A (baseline)"
add_ax_json="${OUT_DIR}/bom_add_a_x.json"
code="$(
  curl -sS -o "$add_ax_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_A_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_X_ID}\",\"quantity\":1,\"uom\":\"EA\",\"find_num\":\"010\",\"refdes\":\"R1\"}"
)"
assert_eq "add A->X http_code" "$code" "200"
assert_eq "add A->X ok" "$(json_get "$add_ax_json" ok)" "True"

add_ay_json="${OUT_DIR}/bom_add_a_y.json"
code="$(
  curl -sS -o "$add_ay_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_A_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_Y_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "add A->Y http_code" "$code" "200"
assert_eq "add A->Y ok" "$(json_get "$add_ay_json" ok)" "True"

log "Build BOM B (changed + added)"
add_bx_json="${OUT_DIR}/bom_add_b_x.json"
code="$(
  curl -sS -o "$add_bx_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_B_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_X_ID}\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"020\",\"refdes\":\"R1,R2\",\"effectivity_from\":\"${effective_from}\"}"
)"
assert_eq "add B->X http_code" "$code" "200"
assert_eq "add B->X ok" "$(json_get "$add_bx_json" ok)" "True"

add_bz_json="${OUT_DIR}/bom_add_b_z.json"
code="$(
  curl -sS -o "$add_bz_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_B_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_Z_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "add B->Z http_code" "$code" "200"
assert_eq "add B->Z ok" "$(json_get "$add_bz_json" ok)" "True"

log "Add substitute to CHILD_X in BOM B"
tree_b_json="${OUT_DIR}/bom_tree_b_depth1.json"
code="$(
  curl -sS -o "$tree_b_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PARENT_B_ID}/tree?depth=1" "${admin_header[@]}"
)"
assert_eq "get BOM tree for B http_code" "$code" "200"
BOM_LINE_X_ID="$("$PY_BIN" - "$tree_b_json" "$CHILD_X_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
child_id = sys.argv[2]
for entry in data.get("children") or []:
  rel = entry.get("relationship") or {}
  child = entry.get("child") or {}
  if child.get("id") == child_id:
    print(rel.get("id") or "")
    raise SystemExit(0)
print("")
PY
)"
assert_nonempty "bom_line_x.id" "$BOM_LINE_X_ID"

sub_add_json="${OUT_DIR}/bom_substitute_add.json"
code="$(
  curl -sS -o "$sub_add_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${BOM_LINE_X_ID}/substitutes" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"${SUB_PART_ID}\",\"properties\":{\"rank\":1}}"
)"
assert_eq "add substitute http_code" "$code" "200"
SUB_REL_ID="$(json_get "$sub_add_json" substitute_id)"
assert_nonempty "substitute.substitute_id" "$SUB_REL_ID"

log "Compare BOM (detailed)"
compare_json="${OUT_DIR}/compare.json"
compare_url="${BASE_URL}/api/v1/bom/compare?left_type=item&left_id=${PARENT_A_ID}&right_type=item&right_id=${PARENT_B_ID}&max_levels=10&line_key=child_config&include_relationship_props=quantity,uom,find_num,refdes,effectivity_from,effectivity_to&include_substitutes=true&include_effectivity=true"
code="$(curl -sS -o "$compare_json" -w "%{http_code}" "$compare_url" "${admin_header[@]}")"
assert_eq "compare http_code" "$code" "200"
"$PY_BIN" - "$compare_json" "$CHILD_X_ID" "$CHILD_Y_ID" "$CHILD_Z_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f)
child_x, child_y, child_z = sys.argv[2], sys.argv[3], sys.argv[4]

summary = d.get("summary") or {}
added = d.get("added") or []
removed = d.get("removed") or []
changed = d.get("changed") or []

def ids(entries):
  out = set()
  for e in entries:
    cid = e.get("child_id") or (e.get("child") or {}).get("id")
    if cid:
      out.add(cid)
  return out

added_ids = ids(added)
removed_ids = ids(removed)
changed_ids = ids(changed)

if int(summary.get("added", len(added))) < 1:
  raise SystemExit("expected >=1 added")
if int(summary.get("removed", len(removed))) < 1:
  raise SystemExit("expected >=1 removed")
if int(summary.get("changed", len(changed))) < 1:
  raise SystemExit("expected >=1 changed")

if child_z not in added_ids:
  raise SystemExit("expected CHILD_Z in added")
if child_y not in removed_ids:
  raise SystemExit("expected CHILD_Y in removed")
if child_x not in changed_ids:
  raise SystemExit("expected CHILD_X in changed")

if int(summary.get("changed_major", 0) or 0) < 1:
  raise SystemExit("expected >=1 changed_major")

target = None
for entry in changed:
  cid = entry.get("child_id") or (entry.get("child") or {}).get("id")
  if cid == child_x:
    target = entry
    break
if not target:
  raise SystemExit("missing changed entry for CHILD_X")

diff_fields = {c.get("field") for c in (target.get("changes") or []) if c.get("field")}
missing = {"quantity", "find_num", "refdes", "substitutes", "effectivities"} - diff_fields
if missing:
  raise SystemExit(f"missing diff fields: {sorted(missing)}")

if target.get("severity") != "major":
  raise SystemExit(f"unexpected severity: {target.get('severity')}")
if not target.get("line_key"):
  raise SystemExit("missing line_key")

before = target.get("before") or {}
after = target.get("after") or {}
def to_float(val):
  try:
    return float(val)
  except Exception:
    return None
if to_float(before.get("quantity")) != 1.0 or to_float(after.get("quantity")) != 2.0:
  raise SystemExit("quantity diff mismatch")
if str(before.get("find_num")) != "010" or str(after.get("find_num")) != "020":
  raise SystemExit("find_num diff mismatch")
before_ref = str(before.get("refdes"))
after_ref = str(after.get("refdes"))
if "R1" not in before_ref or "R1" not in after_ref or "R2" not in after_ref:
  raise SystemExit("refdes diff mismatch")

print("bom_compare_ok=1")
PY

log "Compare BOM (compare_mode=only_product)"
compare_only_json="${OUT_DIR}/compare_only_product.json"
compare_only_url="${BASE_URL}/api/v1/bom/compare?left_type=item&left_id=${PARENT_A_ID}&right_type=item&right_id=${PARENT_B_ID}&max_levels=10&compare_mode=only_product"
code="$(curl -sS -o "$compare_only_json" -w "%{http_code}" "$compare_only_url" "${admin_header[@]}")"
assert_eq "compare only_product http_code" "$code" "200"
"$PY_BIN" - "$compare_only_json" "$CHILD_X_ID" "$CHILD_Y_ID" "$CHILD_Z_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f)
child_x, child_y, child_z = sys.argv[2], sys.argv[3], sys.argv[4]

summary = d.get("summary") or {}
added = d.get("added") or []
removed = d.get("removed") or []
changed = d.get("changed") or []

def ids(entries):
  out = set()
  for e in entries:
    cid = e.get("child_id") or (e.get("child") or {}).get("id")
    if cid:
      out.add(cid)
  return out

added_ids = ids(added)
removed_ids = ids(removed)

if int(summary.get("changed", 0) or 0) != 0 or changed:
  raise SystemExit("only_product should not report changed entries")
if child_z not in added_ids:
  raise SystemExit("only_product: expected CHILD_Z in added")
if child_y not in removed_ids:
  raise SystemExit("only_product: expected CHILD_Y in removed")
if child_x in added_ids or child_x in removed_ids:
  raise SystemExit("only_product: CHILD_X should not be added/removed")
print("bom_compare_only_product_ok=1")
PY

log "Compare BOM (compare_mode=num_qty)"
compare_num_json="${OUT_DIR}/compare_num_qty.json"
compare_num_url="${BASE_URL}/api/v1/bom/compare?left_type=item&left_id=${PARENT_A_ID}&right_type=item&right_id=${PARENT_B_ID}&max_levels=10&compare_mode=num_qty"
code="$(curl -sS -o "$compare_num_json" -w "%{http_code}" "$compare_num_url" "${admin_header[@]}")"
assert_eq "compare num_qty http_code" "$code" "200"
"$PY_BIN" - "$compare_num_json" "$CHILD_X_ID" "$CHILD_Y_ID" "$CHILD_Z_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f)
child_x, child_y, child_z = sys.argv[2], sys.argv[3], sys.argv[4]

summary = d.get("summary") or {}
added = d.get("added") or []
removed = d.get("removed") or []
changed = d.get("changed") or []

def ids(entries):
  out = set()
  for e in entries:
    cid = e.get("child_id") or (e.get("child") or {}).get("id")
    if cid:
      out.add(cid)
  return out

added_ids = ids(added)
removed_ids = ids(removed)

if int(summary.get("changed", 0) or 0) != 0 or changed:
  raise SystemExit("num_qty should not report changed entries")
if child_z not in added_ids:
  raise SystemExit("num_qty: expected CHILD_Z in added")
if child_y not in removed_ids:
  raise SystemExit("num_qty: expected CHILD_Y in removed")
if child_x not in added_ids or child_x not in removed_ids:
  raise SystemExit("num_qty: expected CHILD_X in both added and removed")
print("bom_compare_num_qty_ok=1")
PY

log "Compare BOM (compare_mode=summarized)"
compare_sum_json="${OUT_DIR}/compare_summarized.json"
compare_sum_url="${BASE_URL}/api/v1/bom/compare?left_type=item&left_id=${PARENT_A_ID}&right_type=item&right_id=${PARENT_B_ID}&max_levels=10&compare_mode=summarized"
code="$(curl -sS -o "$compare_sum_json" -w "%{http_code}" "$compare_sum_url" "${admin_header[@]}")"
assert_eq "compare summarized http_code" "$code" "200"
"$PY_BIN" - "$compare_sum_json" "$CHILD_X_ID" "$CHILD_Y_ID" "$CHILD_Z_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f)
child_x, child_y, child_z = sys.argv[2], sys.argv[3], sys.argv[4]

summary = d.get("summary") or {}
added = d.get("added") or []
removed = d.get("removed") or []
changed = d.get("changed") or []

def ids(entries):
  out = set()
  for e in entries:
    cid = e.get("child_id") or (e.get("child") or {}).get("id")
    if cid:
      out.add(cid)
  return out

added_ids = ids(added)
removed_ids = ids(removed)
changed_ids = ids(changed)

if int(summary.get("changed", len(changed))) < 1:
  raise SystemExit("summarized should report changed entries")
if child_z not in added_ids:
  raise SystemExit("summarized: expected CHILD_Z in added")
if child_y not in removed_ids:
  raise SystemExit("summarized: expected CHILD_Y in removed")
if child_x not in changed_ids:
  raise SystemExit("summarized: expected CHILD_X in changed")

target = None
for entry in changed:
  cid = entry.get("child_id") or (entry.get("child") or {}).get("id")
  if cid == child_x:
    target = entry
    break
if not target:
  raise SystemExit("summarized: missing changed entry for CHILD_X")

diff_fields = {c.get("field") for c in (target.get("changes") or []) if c.get("field")}
if "quantity" not in diff_fields:
  raise SystemExit("summarized: expected quantity diff")
extra = diff_fields - {"quantity", "uom"}
if extra:
  raise SystemExit(f"summarized: unexpected diff fields: {sorted(extra)}")

print("bom_compare_summarized_ok=1")
PY

log "PASS: BOM Compare API E2E verification"

