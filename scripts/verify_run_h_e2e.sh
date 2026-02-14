#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for "Run H (Core APIs)".
#
# Coverage:
# - health
# - meta metadata (Part)
# - AML add/get
# - search
# - RPC Item.create
# - file upload/metadata/download
# - BOM effective
# - plugins list + demo ping
# - ECO create/new-revision/approve/apply
# - versions history/tree
# - integrations health (should be 200 even if services are down)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-run-h/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_run_h_${timestamp}.db}"
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

log "Login (admin)"
login_json="${OUT_DIR}/login_admin.json"
code="$(
  curl -sS -o "$login_json" -w "%{http_code}" \
    -X POST "${API}/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
assert_eq "login http_code" "$code" "200"
TOKEN="$("$PY_BIN" - "$login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "access_token" "$TOKEN"

auth_headers=(-H "Authorization: Bearer ${TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")
tenant_headers=(-H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")

log "Health"
health_api_json="${OUT_DIR}/health_api.json"
code="$(
  curl -sS -o "$health_api_json" -w "%{http_code}" \
    "${API}/health" \
    "${tenant_headers[@]}"
)"
assert_eq "health http_code" "$code" "200"
assert_eq "health.ok" "$(json_get "$health_api_json" ok)" "True"

log "Meta metadata (Part)"
meta_part_json="${OUT_DIR}/meta_part_metadata.json"
code="$(
  curl -sS -o "$meta_part_json" -w "%{http_code}" \
    "${API}/aml/metadata/Part" \
    "${auth_headers[@]}"
)"
assert_eq "meta metadata http_code" "$code" "200"
"$PY_BIN" - "$meta_part_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f)
if d.get("id") != "Part":
  raise SystemExit("expected id=Part")
props = [p.get("name") for p in (d.get("properties") or []) if isinstance(p, dict)]
if "item_number" not in props:
  raise SystemExit("expected item_number in metadata properties")
print("meta_part_ok=1")
PY

ts="$(date +%s)"
PN="P-VERIFY-${ts}"

log "AML add (Part)"
part_add_json="${OUT_DIR}/aml_part_add.json"
code="$(
  curl -sS -o "$part_add_json" -w "%{http_code}" \
    -X POST "${API}/aml/apply" \
    "${auth_headers[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${PN}\",\"name\":\"Verify Part ${ts}\"}}"
)"
assert_eq "AML add http_code" "$code" "200"
PART_ID="$(json_get "$part_add_json" id)"
assert_nonempty "part.id" "$PART_ID"

log "AML get (Part)"
part_get_json="${OUT_DIR}/aml_part_get.json"
code="$(
  curl -sS -o "$part_get_json" -w "%{http_code}" \
    -X POST "${API}/aml/apply" \
    "${auth_headers[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"get\",\"properties\":{\"item_number\":\"${PN}\"}}"
)"
assert_eq "AML get http_code" "$code" "200"
"$PY_BIN" - "$part_get_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f) or {}
if int(d.get("count") or 0) < 1:
  raise SystemExit(f"expected count>=1, got {d.get('count')}")
print("aml_get_ok=1")
PY

log "Search"
search_json="${OUT_DIR}/search.json"
code="$(
  curl -sS -o "$search_json" -w "%{http_code}" \
    "${API}/search/?q=${PN}&item_type=Part" \
    "${auth_headers[@]}"
)"
assert_eq "search http_code" "$code" "200"
"$PY_BIN" - "$search_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f) or {}
if int(d.get("total") or 0) < 1:
  raise SystemExit(f"expected total>=1, got {d.get('total')}")
print("search_ok=1")
PY

log "RPC Item.create"
PN2="P-RPC-${ts}"
rpc_json="${OUT_DIR}/rpc_item_create.json"
code="$(
  curl -sS -o "$rpc_json" -w "%{http_code}" \
    -X POST "${API}/rpc/" \
    "${auth_headers[@]}" -H 'content-type: application/json' \
    -d "{\"model\":\"Item\",\"method\":\"create\",\"args\":[{\"type\":\"Part\",\"properties\":{\"item_number\":\"${PN2}\",\"name\":\"RPC Part\"}}],\"kwargs\":{}}"
)"
assert_eq "rpc http_code" "$code" "200"
RPC_ID="$("$PY_BIN" - "$rpc_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f) or {}
print(((d.get("result") or {}) or {}).get("id") or "")
PY
)"
assert_nonempty "rpc.result.id" "$RPC_ID"

log "File upload/metadata/download"
test_file="${OUT_DIR}/run_h_test_${ts}.txt"
echo "yuantus verification test ${ts}" >"$test_file"

upload_json="${OUT_DIR}/file_upload.json"
code="$(
  curl -sS -o "$upload_json" -w "%{http_code}" \
    -X POST "${API}/file/upload?generate_preview=false" \
    "${auth_headers[@]}" \
    -F "file=@${test_file};filename=run_h_test_${ts}.txt"
)"
assert_eq "file upload http_code" "$code" "200"
FILE_ID="$(json_get "$upload_json" id)"
assert_nonempty "file.id" "$FILE_ID"

file_meta_json="${OUT_DIR}/file_metadata.json"
code="$(
  curl -sS -o "$file_meta_json" -w "%{http_code}" \
    "${API}/file/${FILE_ID}" \
    "${auth_headers[@]}"
)"
assert_eq "file metadata http_code" "$code" "200"
assert_eq "file metadata id" "$(json_get "$file_meta_json" id)" "$FILE_ID"

download_headers="${OUT_DIR}/file_download_headers.txt"
download_out="${OUT_DIR}/file_downloaded.txt"
download_url="${API}/file/${FILE_ID}/download"
code="$(
  curl -sS -D "$download_headers" -o "$download_out" -w "%{http_code}" \
    "$download_url" \
    "${auth_headers[@]}"
)"
if [[ "$code" == "200" ]]; then
  :
elif [[ "$code" == "302" || "$code" == "307" || "$code" == "301" || "$code" == "308" ]]; then
  location="$("$PY_BIN" - "$download_headers" <<'PY'
import sys
path = sys.argv[1]
loc = None
with open(path, "r", encoding="utf-8", errors="ignore") as f:
  for line in f:
    if line.lower().startswith("location:"):
      loc = line.split(":", 1)[1].strip()
      break
if not loc:
  raise SystemExit("Missing Location header in redirect response")
print(loc)
PY
)"
  # Follow redirect without leaking API Authorization headers to object storage.
  code2="$(curl -sS -o "$download_out" -w "%{http_code}" "$location")"
  [[ "$code2" == "200" ]] || fail "redirect download failed: HTTP ${code2}"
  code="302->${code2}"
else
  cat "$download_headers" >&2 || true
  fail "download failed: HTTP ${code}"
fi
diff -q "$test_file" "$download_out" >/dev/null || fail "downloaded file content mismatch"

log "BOM effective"
bom_effective_json="${OUT_DIR}/bom_effective.json"
code="$(
  curl -sS -o "$bom_effective_json" -w "%{http_code}" \
    "${API}/bom/${PART_ID}/effective" \
    "${auth_headers[@]}"
)"
assert_eq "bom effective http_code" "$code" "200"
"$PY_BIN" - "$bom_effective_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f) or {}
if "children" not in d:
  raise SystemExit("expected 'children' in bom effective response")
print("bom_effective_ok=1")
PY

log "Plugins list + demo ping"
plugins_json="${OUT_DIR}/plugins_list.json"
code="$(
  curl -sS -o "$plugins_json" -w "%{http_code}" \
    "${API}/plugins" \
    "${auth_headers[@]}"
)"
assert_eq "plugins list http_code" "$code" "200"
assert_eq "plugins list ok" "$(json_get "$plugins_json" ok)" "True"

plugin_ping_json="${OUT_DIR}/plugin_demo_ping.json"
code="$(
  curl -sS -o "$plugin_ping_json" -w "%{http_code}" \
    "${API}/plugins/demo/ping" \
    "${auth_headers[@]}"
)"
assert_eq "plugin ping http_code" "$code" "200"
assert_eq "plugin ping ok" "$(json_get "$plugin_ping_json" ok)" "True"

log "ECO full flow"
stage_json="${OUT_DIR}/eco_stage.json"
code="$(
  curl -sS -o "$stage_json" -w "%{http_code}" \
    -X POST "${API}/eco/stages" \
    "${auth_headers[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"Review-${ts}\",\"sequence\":10,\"approval_type\":\"mandatory\",\"approval_roles\":[\"admin\"]}"
)"
assert_eq "eco stage create http_code" "$code" "200"
STAGE_ID="$(json_get "$stage_json" id)"
assert_nonempty "eco stage id" "$STAGE_ID"

eco_json="${OUT_DIR}/eco_create.json"
code="$(
  curl -sS -o "$eco_json" -w "%{http_code}" \
    -X POST "${API}/eco" \
    "${auth_headers[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"ECO-VERIFY-${ts}\",\"eco_type\":\"bom\",\"product_id\":\"${PART_ID}\",\"description\":\"Verification ECO\",\"priority\":\"normal\"}"
)"
assert_eq "eco create http_code" "$code" "200"
ECO_ID="$(json_get "$eco_json" id)"
assert_nonempty "eco.id" "$ECO_ID"

newrev_json="${OUT_DIR}/eco_new_revision.json"
code="$(
  curl -sS -o "$newrev_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO_ID}/new-revision" \
    "${auth_headers[@]}"
)"
assert_eq "eco new-revision http_code" "$code" "200"
assert_eq "eco new-revision success" "$(json_get "$newrev_json" success)" "True"
VERSION_ID="$(json_get "$newrev_json" version_id)"
assert_nonempty "eco new-revision version_id" "$VERSION_ID"

approve_json="${OUT_DIR}/eco_approve.json"
code="$(
  curl -sS -o "$approve_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO_ID}/approve" \
    "${auth_headers[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"verification approved\"}"
)"
assert_eq "eco approve http_code" "$code" "200"
assert_eq "eco approve status" "$(json_get "$approve_json" status)" "approved"

apply_json="${OUT_DIR}/eco_apply.json"
code="$(
  curl -sS -o "$apply_json" -w "%{http_code}" \
    -X POST "${API}/eco/${ECO_ID}/apply" \
    "${auth_headers[@]}"
)"
assert_eq "eco apply http_code" "$code" "200"
assert_eq "eco apply success" "$(json_get "$apply_json" success)" "True"

log "Versions history/tree"
ver_hist_json="${OUT_DIR}/versions_history.json"
code="$(
  curl -sS -o "$ver_hist_json" -w "%{http_code}" \
    "${API}/versions/items/${PART_ID}/history" \
    "${auth_headers[@]}"
)"
assert_eq "versions history http_code" "$code" "200"
"$PY_BIN" - "$ver_hist_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f)
if not isinstance(d, list) or len(d) < 1:
  raise SystemExit("expected non-empty history list")
print("versions_history_ok=1")
PY

ver_tree_json="${OUT_DIR}/versions_tree.json"
code="$(
  curl -sS -o "$ver_tree_json" -w "%{http_code}" \
    "${API}/versions/items/${PART_ID}/tree" \
    "${auth_headers[@]}"
)"
assert_eq "versions tree http_code" "$code" "200"
"$PY_BIN" - "$ver_tree_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f)
if not isinstance(d, list) or len(d) < 1:
  raise SystemExit("expected non-empty tree list")
print("versions_tree_ok=1")
PY

log "Integrations health"
integrations_json="${OUT_DIR}/integrations_health.json"
code="$(
  curl -sS -o "$integrations_json" -w "%{http_code}" \
    "${API}/integrations/health" \
    "${tenant_headers[@]}" \
    -H "Authorization: Bearer ${TOKEN}"
)"
assert_eq "integrations health http_code" "$code" "200"
"$PY_BIN" - "$integrations_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  d = json.load(f) or {}
if "services" not in d:
  raise SystemExit("expected services in integrations health response")
print("integrations_health_ok=1")
PY

log "PASS: Run H core APIs E2E verification"

