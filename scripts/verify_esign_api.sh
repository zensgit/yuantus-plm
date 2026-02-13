#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for the Electronic Signature subsystem.
#
# Coverage:
# - admin-only signing reason + manifest creation
# - sign (with password verification) + verify
# - revoke + verify invalid + list signatures include_revoked behavior
# - audit logs + audit export CSV
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-esign/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_esign_${timestamp}.db}"
db_path_norm="${DB_PATH#/}"

export PYTHONPATH="${PYTHONPATH:-src}"

# Force an isolated ephemeral DB for this verification, even if the caller has
# YUANTUS_* env vars set (e.g., running via scripts/verify_all.sh).
export YUANTUS_TENANCY_MODE="single"
export YUANTUS_SCHEMA_MODE="create_all"
export YUANTUS_DATABASE_URL="sqlite:////${db_path_norm}"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:////${db_path_norm}"

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

log "Login"
login_json="${OUT_DIR}/login.json"
code="$(
  curl -sS -o "$login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_json" >&2 || true
  fail "login -> HTTP $code"
fi

TOKEN="$("$PY_BIN" - "$login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
if [[ -z "$TOKEN" ]]; then
  fail "failed to parse access_token"
fi

auth_header=(-H "Authorization: Bearer ${TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")
json_header=(-H "content-type: application/json")

request_json() {
  local method="$1"
  local path="$2"
  local out_path="$3"
  local data="${4:-}"

  local url="${BASE_URL}${path}"
  local http_code
  if [[ -n "$data" ]]; then
    http_code="$(curl -sS -o "$out_path" -w "%{http_code}" -X "$method" "$url" "${auth_header[@]}" "${json_header[@]}" -d "$data")"
  else
    http_code="$(curl -sS -o "$out_path" -w "%{http_code}" -X "$method" "$url" "${auth_header[@]}")"
  fi

  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    cat "$out_path" >&2 || true
    fail "${method} ${path} -> HTTP ${http_code} (out: ${out_path})"
  fi
}

request_raw() {
  local method="$1"
  local path="$2"
  local out_path="$3"

  local url="${BASE_URL}${path}"
  local http_code
  http_code="$(curl -sS -o "$out_path" -w "%{http_code}" -X "$method" "$url" "${auth_header[@]}")"

  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    cat "$out_path" >&2 || true
    fail "${method} ${path} -> HTTP ${http_code} (out: ${out_path})"
  fi
}

json_id() {
  "$PY_BIN" - "$1" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
print(data.get("id") or "")
PY
}

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

log "Create an item to sign (AML)"
ts="$(date +%s)"
item_number="ESIGN-${ts}"
item_json="${OUT_DIR}/item_create.json"
request_json POST "/api/v1/aml/apply" "$item_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${item_number}\",\"name\":\"E-sign Target ${ts}\"}}"
item_id="$(json_id "$item_json")"
[[ -n "$item_id" ]] || fail "failed to parse item id"
item_generation="1"

log "Create a signing reason (requires_password=true)"
reason_json="${OUT_DIR}/esign_reason_create.json"
request_json POST "/api/v1/esign/reasons" "$reason_json" \
  "{\"code\":\"approve\",\"name\":\"Approve\",\"meaning\":\"approved\",\"description\":\"E2E test reason\",\"requires_password\":true,\"requires_comment\":false,\"sequence\":10}"
reason_id="$(json_get "$reason_json" id)"
[[ -n "$reason_id" ]] || fail "failed to parse reason id"

log "Create a manifest (approved required)"
manifest_create_json="${OUT_DIR}/esign_manifest_create.json"
request_json POST "/api/v1/esign/manifests" "$manifest_create_json" \
  "{\"item_id\":\"${item_id}\",\"generation\":${item_generation},\"required_signatures\":[{\"meaning\":\"approved\",\"role\":\"admin\",\"required\":true}]}"
manifest_complete="$(json_get "$manifest_create_json" is_complete)"
assert_eq "manifest.is_complete" "$manifest_complete" "False"

log "Sign (with password) + verify"
sign_json="${OUT_DIR}/esign_sign.json"
request_json POST "/api/v1/esign/sign" "$sign_json" \
  "{\"item_id\":\"${item_id}\",\"meaning\":\"approved\",\"password\":\"${PASSWORD}\",\"reason_id\":\"${reason_id}\",\"comment\":\"\"}"
signature_id="$(json_get "$sign_json" id)"
[[ -n "$signature_id" ]] || fail "failed to parse signature id"

verify_json="${OUT_DIR}/esign_verify.json"
request_json POST "/api/v1/esign/verify/${signature_id}" "$verify_json"
assert_eq "verify.is_valid" "$(json_get "$verify_json" is_valid)" "True"

log "Manifest should now be complete"
manifest_status_json="${OUT_DIR}/esign_manifest_status.json"
request_json GET "/api/v1/esign/manifests/${item_id}" "$manifest_status_json"
assert_eq "manifest_status.is_complete" "$(json_get "$manifest_status_json" is_complete)" "True"

log "List signatures (default excludes revoked)"
sigs_json="${OUT_DIR}/esign_signatures.json"
request_json GET "/api/v1/esign/items/${item_id}/signatures" "$sigs_json"
"$PY_BIN" - "$sigs_json" "$signature_id" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
items = data.get("items") or []
sid = sys.argv[2]
if not any(isinstance(s, dict) and s.get("id") == sid for s in items):
  raise SystemExit("expected signature in list_signatures response")
print(f"signatures_total={len(items)}")
PY

log "Revoke signature"
revoke_json="${OUT_DIR}/esign_revoke.json"
request_json POST "/api/v1/esign/revoke/${signature_id}" "$revoke_json" "{\"reason\":\"E2E revoke\"}"
assert_eq "revoke.status" "$(json_get "$revoke_json" status)" "revoked"

log "Verify after revoke should be invalid"
verify2_json="${OUT_DIR}/esign_verify_after_revoke.json"
request_json POST "/api/v1/esign/verify/${signature_id}" "$verify2_json"
assert_eq "verify_after_revoke.is_valid" "$(json_get "$verify2_json" is_valid)" "False"

log "List signatures should be empty unless include_revoked=true"
sigs_after_json="${OUT_DIR}/esign_signatures_after_revoke.json"
request_json GET "/api/v1/esign/items/${item_id}/signatures" "$sigs_after_json"
"$PY_BIN" - "$sigs_after_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
items = data.get("items") or []
if items:
  raise SystemExit("expected empty signature list after revoke (include_revoked=false)")
print("signatures_after_revoke_total=0")
PY

sigs_revoked_json="${OUT_DIR}/esign_signatures_include_revoked.json"
request_json GET "/api/v1/esign/items/${item_id}/signatures?include_revoked=true" "$sigs_revoked_json"
"$PY_BIN" - "$sigs_revoked_json" "$signature_id" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
items = data.get("items") or []
sid = sys.argv[2]
if not any(isinstance(s, dict) and s.get("id") == sid for s in items):
  raise SystemExit("expected revoked signature in include_revoked list")
print(f"signatures_include_revoked_total={len(items)}")
PY

log "Audit logs + export"
audit_logs_json="${OUT_DIR}/esign_audit_logs.json"
request_json GET "/api/v1/esign/audit-logs?item_id=${item_id}&limit=50&offset=0" "$audit_logs_json"
"$PY_BIN" - "$audit_logs_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
items = data.get("items") or []
if len(items) < 2:
  raise SystemExit("expected at least 2 audit log entries")
print(f"audit_logs_total={len(items)}")
PY

audit_csv="${OUT_DIR}/esign_audit_export.csv"
request_raw GET "/api/v1/esign/audit-logs/export?export_format=csv&item_id=${item_id}&limit=2000&offset=0" "$audit_csv"
"$PY_BIN" - "$audit_csv" <<'PY'
import sys
from pathlib import Path

p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8", errors="replace")
lines = [ln for ln in text.splitlines() if ln.strip()]
if len(lines) < 2:
  raise SystemExit("expected CSV header + at least one row")
header = lines[0].lower()
for col in ["id", "action", "actor_username", "timestamp"]:
  if col not in header:
    raise SystemExit(f"expected column in csv header: {col}")
print(f"audit_export_rows={len(lines)-1}")
PY

log "ALL CHECKS PASSED out=${OUT_DIR}"

