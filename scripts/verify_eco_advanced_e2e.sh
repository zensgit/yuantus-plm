#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for ECO Advanced full flow.
#
# Coverage:
# - stage create + move stage
# - overdue approvals list + notify
# - new revision (target version) + apply
# - where-used impact (assembly -> product)
# - BOM diff + compare_mode guardrail (only_product)
# - impact analysis (include files + bom diff + version diffs)
# - impact export (csv/xlsx/pdf)
# - batch approvals (admin ok, viewer denied)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-eco-advanced/${timestamp}"
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
API="${BASE_URL}/api/v1"

TENANT_ID="${TENANT_ID:-tenant-1}"
ORG_ID="${ORG_ID:-org-1}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"
VIEWER_USERNAME="${VIEWER_USERNAME:-viewer}"
VIEWER_PASSWORD="${VIEWER_PASSWORD:-viewer}"

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_eco_advanced_${timestamp}.db}"
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
  if curl -fsS "${API}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "${API}/health" >"${OUT_DIR}/health.json" || fail "health failed (see ${server_log})"

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

ts="$(date +%s)"

log "Login (admin)"
login_admin_json="${OUT_DIR}/login_admin.json"
code="$(
  curl -sS -o "$login_admin_json" -w "%{http_code}" \
    -X POST "${API}/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
assert_eq "admin login http_code" "$code" "200"
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
    -X POST "${API}/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${VIEWER_USERNAME}\",\"password\":\"${VIEWER_PASSWORD}\"}"
)"
assert_eq "viewer login http_code" "$code" "200"
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

log "Create ECO stage (approval_roles=admin)"
stage_json="${OUT_DIR}/eco_stage_create.json"
code="$(
  curl -sS -o "$stage_json" -w "%{http_code}" \
    -X POST "${API}/eco/stages" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"S4-Review-${ts}\",\"sequence\":90,\"approval_type\":\"mandatory\",\"approval_roles\":[\"admin\"],\"auto_progress\":false,\"is_blocking\":false,\"sla_hours\":0}"
)"
assert_eq "create stage http_code" "$code" "200"
STAGE_ID="$(json_get "$stage_json" id)"
assert_nonempty "stage.id" "$STAGE_ID"

create_part() {
  local out="$1"
  local number="$2"
  local name="$3"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      -X POST "${API}/aml/apply" \
      "${admin_header[@]}" -H 'content-type: application/json' \
      -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${number}\",\"name\":\"${name}\"}}"
  )"
  [[ "$http_code" == "200" ]] || fail "create part ${number} -> HTTP ${http_code} (out=${out})"
  json_get "$out" id
}

log "Create product + assembly"
PRODUCT_ID="$(create_part "${OUT_DIR}/product.json" "ECO-P-${ts}" "ECO Product ${ts}")"
ASSEMBLY_ID="$(create_part "${OUT_DIR}/assembly.json" "ECO-A-${ts}" "ECO Assembly ${ts}")"
assert_nonempty "product.id" "$PRODUCT_ID"
assert_nonempty "assembly.id" "$ASSEMBLY_ID"

log "Init product version"
init_json="${OUT_DIR}/product_version_init.json"
code="$(
  curl -sS -o "$init_json" -w "%{http_code}" \
    -X POST "${API}/versions/items/${PRODUCT_ID}/init" \
    "${admin_header[@]}"
)"
assert_eq "init version http_code" "$code" "200"
INIT_VERSION_ID="$(json_get "$init_json" id)"
assert_nonempty "init_version.id" "$INIT_VERSION_ID"

log "Build where-used link (assembly -> product)"
where_used_json="${OUT_DIR}/where_used_link.json"
code="$(
  curl -sS -o "$where_used_json" -w "%{http_code}" \
    -X POST "${API}/bom/${ASSEMBLY_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${PRODUCT_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "where_used link http_code" "$code" "200"
assert_eq "where_used link ok" "$(json_get "$where_used_json" ok)" "True"

log "Upload file + attach to product"
upload_file="${OUT_DIR}/eco_impact_${ts}.txt"
echo "yuantus eco impact verification ${ts}" >"$upload_file"

upload_json="${OUT_DIR}/file_upload.json"
code="$(
  curl -sS -o "$upload_json" -w "%{http_code}" \
    -X POST "${API}/file/upload?generate_preview=false" \
    "${admin_header[@]}" \
    -F "file=@${upload_file};filename=eco_impact_${ts}.txt"
)"
assert_eq "file upload http_code" "$code" "200"
FILE_ID="$(json_get "$upload_json" id)"
assert_nonempty "upload.id" "$FILE_ID"

attach_json="${OUT_DIR}/file_attach.json"
code="$(
  curl -sS -o "$attach_json" -w "%{http_code}" \
    -X POST "${API}/file/attach" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"item_id\":\"${PRODUCT_ID}\",\"file_id\":\"${FILE_ID}\",\"file_role\":\"native_cad\"}"
)"
assert_eq "file attach http_code" "$code" "200"
assert_nonempty "attach.status" "$(json_get "$attach_json" status)"

log "Checkout + checkin to sync version files"
checkout_json="${OUT_DIR}/product_checkout.json"
code="$(
  curl -sS -o "$checkout_json" -w "%{http_code}" \
    -X POST "${API}/versions/items/${PRODUCT_ID}/checkout" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"checkout for version file binding\"}"
)"
assert_eq "checkout http_code" "$code" "200"
assert_nonempty "checkout.id" "$(json_get "$checkout_json" id)"

checkin_json="${OUT_DIR}/product_checkin.json"
code="$(
  curl -sS -o "$checkin_json" -w "%{http_code}" \
    -X POST "${API}/versions/items/${PRODUCT_ID}/checkin" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"checkin after version file binding\"}"
)"
assert_eq "checkin http_code" "$code" "200"
assert_nonempty "checkin.id" "$(json_get "$checkin_json" id)"

init_files_json="${OUT_DIR}/init_version_files.json"
code="$(
  curl -sS -o "$init_files_json" -w "%{http_code}" \
    "${API}/versions/${INIT_VERSION_ID}/files" \
    "${admin_header[@]}"
)"
assert_eq "init version files http_code" "$code" "200"
"$PY_BIN" - "$init_files_json" "$FILE_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or []
file_id = sys.argv[2]
roles = [x.get("file_role") for x in data if x.get("file_id") == file_id]
if "native_cad" not in roles:
  raise SystemExit(f"expected native_cad file in init version files, got roles={roles}")
print("init_version_files_ok=1")
PY

log "Create ECO1 (for product)"
eco1_json="${OUT_DIR}/eco1_create.json"
code="$(
  curl -sS -o "$eco1_json" -w "%{http_code}" \
    -X POST "${API}/eco" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"ECO-ADV-${ts}\",\"eco_type\":\"bom\",\"product_id\":\"${PRODUCT_ID}\",\"description\":\"ECO advanced verification\"}"
)"
assert_eq "eco1 create http_code" "$code" "200"
ECO1_ID="$(json_get "$eco1_json" id)"
assert_nonempty "eco1.id" "$ECO1_ID"

log "Move ECO1 to approval stage"
eco1_move_json="${OUT_DIR}/eco1_move_stage.json"
code="$(
  curl -sS -o "$eco1_move_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO1_ID}/move-stage" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"stage_id\":\"${STAGE_ID}\"}"
)"
assert_eq "eco1 move stage http_code" "$code" "200"

log "SLA overdue check + notify"
overdue_json="${OUT_DIR}/eco_overdue.json"
code="$(
  curl -sS -o "$overdue_json" -w "%{http_code}" \
    "${API}/eco/approvals/overdue" \
    "${admin_header[@]}"
)"
assert_eq "overdue http_code" "$code" "200"
"$PY_BIN" - "$overdue_json" "$ECO1_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or []
eco_id = sys.argv[2]
ids = [x.get("eco_id") for x in data if isinstance(x, dict)]
if eco_id not in ids:
  raise SystemExit("Expected ECO1 in overdue list")
print("overdue_ok=1")
PY

notify_json="${OUT_DIR}/eco_notify_overdue.json"
code="$(
  curl -sS -o "$notify_json" -w "%{http_code}" \
    -X POST "${API}/eco/approvals/notify-overdue" \
    "${admin_header[@]}"
)"
assert_eq "notify overdue http_code" "$code" "200"
"$PY_BIN" - "$notify_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or {}
if int(data.get("count") or 0) < 1 or int(data.get("notified") or 0) < 1:
  raise SystemExit(f"Expected overdue notifications, got {data}")
print("notify_ok=1")
PY

log "Create ECO target version"
new_rev_json="${OUT_DIR}/eco1_new_revision.json"
code="$(
  curl -sS -o "$new_rev_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO1_ID}/new-revision" \
    "${admin_header[@]}"
)"
assert_eq "new revision http_code" "$code" "200"
TARGET_VERSION_ID="$(json_get "$new_rev_json" version_id)"
assert_nonempty "target_version_id" "$TARGET_VERSION_ID"

log "Resolve target version timestamp"
tree_json="${OUT_DIR}/versions_tree.json"
code="$(
  curl -sS -o "$tree_json" -w "%{http_code}" \
    "${API}/versions/items/${PRODUCT_ID}/tree" \
    "${admin_header[@]}"
)"
assert_eq "versions tree http_code" "$code" "200"
TARGET_CREATED_AT="$("$PY_BIN" - "$tree_json" "$TARGET_VERSION_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or []
target_id = sys.argv[2]
created = ""
for node in data:
  if (node or {}).get("id") == target_id:
    created = (node or {}).get("created_at") or ""
    break
print(created)
PY
)"
assert_nonempty "target_created_at" "$TARGET_CREATED_AT"

log "Approve ECO1 (required for apply)"
eco1_approve_json="${OUT_DIR}/eco1_approve.json"
code="$(
  curl -sS -o "$eco1_approve_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO1_ID}/approve" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"approve for apply\"}"
)"
assert_eq "eco1 approve http_code" "$code" "200"

eco1_get_preapply_json="${OUT_DIR}/eco1_get_preapply.json"
code="$(
  curl -sS -o "$eco1_get_preapply_json" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}" \
    "${admin_header[@]}"
)"
assert_eq "eco1 get preapply http_code" "$code" "200"
assert_eq "eco1 state preapply" "$(json_get "$eco1_get_preapply_json" state)" "approved"

log "ECO apply diagnostics"
eco1_diag_json="${OUT_DIR}/eco1_apply_diagnostics.json"
code="$(
  curl -sS -o "$eco1_diag_json" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}/apply-diagnostics?ruleset_id=default" \
    "${admin_header[@]}"
)"
assert_eq "eco apply diagnostics http_code" "$code" "200"
assert_eq "eco apply diagnostics ok" "$(json_get "$eco1_diag_json" ok)" "True"

log "ECO apply + verify version files synced to item"
eco_apply_json="${OUT_DIR}/eco1_apply.json"
code="$(
  curl -sS -o "$eco_apply_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO1_ID}/apply" \
    "${admin_header[@]}"
)"
assert_eq "eco apply http_code" "$code" "200"

eco1_get_postapply_json="${OUT_DIR}/eco1_get_postapply.json"
code="$(
  curl -sS -o "$eco1_get_postapply_json" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}" \
    "${admin_header[@]}"
)"
assert_eq "eco1 get postapply http_code" "$code" "200"
assert_eq "eco1 state postapply" "$(json_get "$eco1_get_postapply_json" state)" "done"

item_files_json="${OUT_DIR}/item_files.json"
code="$(
  curl -sS -o "$item_files_json" -w "%{http_code}" \
    "${API}/file/item/${PRODUCT_ID}" \
    "${admin_header[@]}"
)"
assert_eq "item files http_code" "$code" "200"
"$PY_BIN" - "$item_files_json" "$FILE_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or []
file_id = sys.argv[2]
if not any((x or {}).get("file_id") == file_id for x in data):
  raise SystemExit("Expected item file to include version native_cad file after ECO apply")
print("item_files_ok=1")
PY

target_files_json="${OUT_DIR}/target_version_files.json"
code="$(
  curl -sS -o "$target_files_json" -w "%{http_code}" \
    "${API}/versions/${TARGET_VERSION_ID}/files" \
    "${admin_header[@]}"
)"
assert_eq "target version files http_code" "$code" "200"
"$PY_BIN" - "$target_files_json" "$FILE_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or []
file_id = sys.argv[2]
roles = [x.get("file_role") for x in data if x.get("file_id") == file_id]
if "native_cad" not in roles:
  raise SystemExit(f"Expected target version to contain native_cad file, got roles={roles}")
print("target_version_files_ok=1")
PY

log "Add new BOM line effective from target version date"
CHILD_ID="$(create_part "${OUT_DIR}/child.json" "ECO-C-${ts}" "ECO Child ${ts}")"
assert_nonempty "child.id" "$CHILD_ID"

add_line_json="${OUT_DIR}/bom_add_effective_line.json"
payload="$(printf '{"child_id":"%s","quantity":1,"uom":"EA","effectivity_from":"%s"}' "$CHILD_ID" "$TARGET_CREATED_AT")"
code="$(
  curl -sS -o "$add_line_json" -w "%{http_code}" \
    -X POST "${API}/bom/${PRODUCT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "$payload"
)"
assert_eq "add effective bom line http_code" "$code" "200"
assert_eq "add effective bom line ok" "$(json_get "$add_line_json" ok)" "True"

log "ECO BOM diff (expect added child)"
bom_diff_json="${OUT_DIR}/eco_bom_diff.json"
code="$(
  curl -sS -o "$bom_diff_json" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}/bom-diff?max_levels=5&include_relationship_props=quantity" \
    "${admin_header[@]}"
)"
assert_eq "bom diff http_code" "$code" "200"
"$PY_BIN" - "$bom_diff_json" "$CHILD_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or {}
summary = data.get("summary") or {}
added = data.get("added") or []
child_id = sys.argv[2]

def ids(entries):
  out = set()
  for e in entries:
    if not isinstance(e, dict):
      continue
    cid = e.get("child_id")
    if not cid:
      child = e.get("child") or {}
      cid = child.get("id")
    if cid:
      out.add(cid)
  return out

added_ids = ids(added)
if int(summary.get("added") or len(added)) < 1:
  raise SystemExit("Expected >=1 added BOM lines")
if child_id not in added_ids:
  raise SystemExit("Expected child id in added set")
print("bom_diff_ok=1")
PY

log "ECO BOM diff (compare_mode=only_product)"
bom_diff_only_json="${OUT_DIR}/eco_bom_diff_only_product.json"
code="$(
  curl -sS -o "$bom_diff_only_json" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}/bom-diff?max_levels=5&compare_mode=only_product" \
    "${admin_header[@]}"
)"
assert_eq "bom diff only_product http_code" "$code" "200"
"$PY_BIN" - "$bom_diff_only_json" "$CHILD_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or {}
summary = data.get("summary") or {}
changed = data.get("changed") or []
added = data.get("added") or []
child_id = sys.argv[2]

if int(summary.get("changed") or 0) != 0 or changed:
  raise SystemExit("only_product should not report changed entries")

added_ids = set()
for e in added:
  if not isinstance(e, dict):
    continue
  added_ids.add(e.get("child_id") or (e.get("child") or {}).get("id"))

if child_id not in added_ids:
  raise SystemExit("Expected child id in added set (only_product)")
print("bom_diff_only_ok=1")
PY

log "ECO impact analysis (include files + bom diff + version diff)"
impact_json="${OUT_DIR}/eco_impact.json"
code="$(
  curl -sS -o "$impact_json" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}/impact?include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity&include_child_fields=true" \
    "${admin_header[@]}"
)"
assert_eq "impact http_code" "$code" "200"
"$PY_BIN" - "$impact_json" "$ASSEMBLY_ID" "$FILE_ID" "$CHILD_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or {}

assembly_id = sys.argv[2]
file_id = sys.argv[3]
child_id = sys.argv[4]

impact_count = int(data.get("impact_count") or 0)
if impact_count < 1:
  raise SystemExit("Expected impact_count >= 1")

assemblies = data.get("impacted_assemblies") or []
parent_ids = []
for a in assemblies:
  if not isinstance(a, dict):
    continue
  parent_ids.append(((a.get("parent") or {}) or {}).get("id"))
if assembly_id not in parent_ids:
  raise SystemExit("Expected assembly to appear in impacted_assemblies")

files = data.get("files") or {}
item_files = files.get("item_files") or []
if not any((f or {}).get("file_id") == file_id for f in item_files):
  raise SystemExit("Expected attached file in files.item_files")

bom_diff = data.get("bom_diff") or {}
summary = bom_diff.get("summary") or {}
added = bom_diff.get("added") or []
added_ids = set()
for e in added:
  if not isinstance(e, dict):
    continue
  added_ids.add(e.get("child_id") or (e.get("child") or {}).get("id"))
if int(summary.get("added") or 0) < 1:
  raise SystemExit("Expected bom_diff.summary.added >= 1")
if child_id not in added_ids:
  raise SystemExit("Expected child id in bom_diff.added")

version_diff = data.get("version_diff")
if version_diff is None:
  raise SystemExit("Expected version_diff in impact response")
if not isinstance(version_diff.get("diffs", {}), dict):
  raise SystemExit("Expected version_diff.diffs to be a dict")

version_files_diff = data.get("version_files_diff")
if version_files_diff is None:
  raise SystemExit("Expected version_files_diff in impact response")
summary_files = version_files_diff.get("summary") or {}
for key in ("added_count", "removed_count", "modified_count"):
  if key not in summary_files:
    raise SystemExit(f"Missing version_files_diff.summary.{key}")

impact_level = data.get("impact_level")
if impact_level not in {"high", "medium", "low", "none"}:
  raise SystemExit("Missing or invalid impact_level")
impact_scope = data.get("impact_scope")
if not impact_scope:
  raise SystemExit("Missing impact_scope")

impact_summary = data.get("impact_summary") or {}
if int(impact_summary.get("added") or 0) < 1:
  raise SystemExit("Expected impact_summary.added >= 1")
if int(impact_summary.get("added") or 0) != int(summary.get("added") or 0):
  raise SystemExit("impact_summary and bom_diff.summary mismatch")

if impact_level != "high":
  raise SystemExit(f"Expected impact_level=high, got {impact_level}")

print("impact_ok=1")
PY

log "ECO impact export (csv/xlsx/pdf)"
csv_out="${OUT_DIR}/impact_export.csv"
xlsx_out="${OUT_DIR}/impact_export.xlsx"
pdf_out="${OUT_DIR}/impact_export.pdf"

code="$(
  curl -sS -o "$csv_out" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}/impact/export?format=csv&include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity&compare_mode=only_product" \
    "${admin_header[@]}"
)"
assert_eq "impact export csv http_code" "$code" "200"

code="$(
  curl -sS -o "$xlsx_out" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}/impact/export?format=xlsx&include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity" \
    "${admin_header[@]}"
)"
assert_eq "impact export xlsx http_code" "$code" "200"

code="$(
  curl -sS -o "$pdf_out" -w "%{http_code}" \
    "${API}/eco/${ECO1_ID}/impact/export?format=pdf&include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity" \
    "${admin_header[@]}"
)"
assert_eq "impact export pdf http_code" "$code" "200"

CSV_PATH="$csv_out" XLSX_PATH="$xlsx_out" PDF_PATH="$pdf_out" "$PY_BIN" - <<'PY'
import os
import pathlib

csv_path = pathlib.Path(os.environ["CSV_PATH"])
xlsx_path = pathlib.Path(os.environ["XLSX_PATH"])
pdf_path = pathlib.Path(os.environ["PDF_PATH"])

csv_text = csv_path.read_text(encoding="utf-8", errors="ignore")
if csv_path.stat().st_size == 0:
  raise SystemExit("CSV export is empty")
if "# Overview" not in csv_text:
  raise SystemExit("CSV export missing Overview section")
if "bom_compare_mode,only_product" not in csv_text:
  raise SystemExit("CSV export missing bom_compare_mode")
if "bom_line_key,child_config" not in csv_text:
  raise SystemExit("CSV export missing bom_line_key")

if xlsx_path.read_bytes()[:2] != b"PK":
  raise SystemExit("XLSX export missing PK header")
if not pdf_path.read_bytes().startswith(b"%PDF"):
  raise SystemExit("PDF export missing %PDF header")
print("impact_export_ok=1")
PY

log "Create ECO2 for batch approvals"
PRODUCT2_ID="$(create_part "${OUT_DIR}/product2.json" "ECO-P2-${ts}" "ECO Product 2 ${ts}")"
assert_nonempty "product2.id" "$PRODUCT2_ID"

eco2_json="${OUT_DIR}/eco2_create.json"
code="$(
  curl -sS -o "$eco2_json" -w "%{http_code}" \
    -X POST "${API}/eco" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"ECO-ADV2-${ts}\",\"eco_type\":\"bom\",\"product_id\":\"${PRODUCT2_ID}\"}"
)"
assert_eq "eco2 create http_code" "$code" "200"
ECO2_ID="$(json_get "$eco2_json" id)"
assert_nonempty "eco2.id" "$ECO2_ID"

eco2_move_json="${OUT_DIR}/eco2_move_stage.json"
code="$(
  curl -sS -o "$eco2_move_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO2_ID}/move-stage" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"stage_id\":\"${STAGE_ID}\"}"
)"
assert_eq "eco2 move stage http_code" "$code" "200"

PRODUCT3_ID="$(create_part "${OUT_DIR}/product3.json" "ECO-P3-${ts}" "ECO Product 3 ${ts}")"
assert_nonempty "product3.id" "$PRODUCT3_ID"

eco3_json="${OUT_DIR}/eco3_create.json"
code="$(
  curl -sS -o "$eco3_json" -w "%{http_code}" \
    -X POST "${API}/eco" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"ECO-ADV3-${ts}\",\"eco_type\":\"bom\",\"product_id\":\"${PRODUCT3_ID}\"}"
)"
assert_eq "eco3 create http_code" "$code" "200"
ECO3_ID="$(json_get "$eco3_json" id)"
assert_nonempty "eco3.id" "$ECO3_ID"

eco3_move_json="${OUT_DIR}/eco3_move_stage.json"
code="$(
  curl -sS -o "$eco3_move_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO3_ID}/move-stage" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"stage_id\":\"${STAGE_ID}\"}"
)"
assert_eq "eco3 move stage http_code" "$code" "200"

log "Batch approve as admin"
batch_admin_json="${OUT_DIR}/batch_approve_admin.json"
code="$(
  curl -sS -o "$batch_admin_json" -w "%{http_code}" \
    -X POST "${API}/eco/approvals/batch" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"eco_ids\":[\"${ECO2_ID}\",\"${ECO3_ID}\"],\"mode\":\"approve\",\"comment\":\"batch approve\"}"
)"
assert_eq "batch approve admin http_code" "$code" "200"
"$PY_BIN" - "$batch_admin_json" "$ECO2_ID" "$ECO3_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or {}
eco2 = sys.argv[2]
eco3 = sys.argv[3]
results = data.get("results") or []
summary = data.get("summary") or {}
status = {r.get("eco_id"): r.get("ok") for r in results if isinstance(r, dict)}
if status.get(eco2) is not True or status.get(eco3) is not True:
  raise SystemExit(f"Expected both approvals to succeed, got {status}")
if int(summary.get("ok") or 0) < 2:
  raise SystemExit(f"Expected summary.ok >= 2, got {summary}")
print("batch_admin_ok=1")
PY

log "Verify ECO states are approved"
eco2_get_json="${OUT_DIR}/eco2_get.json"
code="$(
  curl -sS -o "$eco2_get_json" -w "%{http_code}" \
    "${API}/eco/${ECO2_ID}" \
    "${admin_header[@]}"
)"
assert_eq "eco2 get http_code" "$code" "200"
eco3_get_json="${OUT_DIR}/eco3_get.json"
code="$(
  curl -sS -o "$eco3_get_json" -w "%{http_code}" \
    "${API}/eco/${ECO3_ID}" \
    "${admin_header[@]}"
)"
assert_eq "eco3 get http_code" "$code" "200"
assert_eq "eco2 state" "$(json_get "$eco2_get_json" state)" "approved"
assert_eq "eco3 state" "$(json_get "$eco3_get_json" state)" "approved"

log "Batch approve as viewer (expect denied)"
batch_viewer_json="${OUT_DIR}/batch_approve_viewer_denied.json"
code="$(
  curl -sS -o "$batch_viewer_json" -w "%{http_code}" \
    -X POST "${API}/eco/approvals/batch" \
    "${viewer_header[@]}" -H 'content-type: application/json' \
    -d "{\"eco_ids\":[\"${ECO2_ID}\",\"${ECO3_ID}\"],\"mode\":\"approve\"}"
)"
assert_eq "batch approve viewer http_code" "$code" "200"
"$PY_BIN" - "$batch_viewer_json" "$ECO2_ID" "$ECO3_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f) or {}
eco2 = sys.argv[2]
eco3 = sys.argv[3]
results = data.get("results") or []
status = {r.get("eco_id"): r.get("ok") for r in results if isinstance(r, dict)}
if status.get(eco2) is not False or status.get(eco3) is not False:
  raise SystemExit(f"Expected viewer approvals to fail, got {status}")
print("batch_viewer_denied_ok=1")
PY

log "PASS: ECO Advanced E2E verification"
