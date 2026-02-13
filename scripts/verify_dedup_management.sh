#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Dedup management endpoints.
#
# Coverage:
# - admin-only dedup rule CRUD (create/list/get)
# - similarity record list/get/review
# - Part Equivalent relationship auto-creation via review(create_relationship=true)
# - operational report + CSV export with rule_id filter (sqlite json_extract path)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-dedup-management/${timestamp}"
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
NONADMIN_USERNAME="${NONADMIN_USERNAME:-viewer}"
NONADMIN_PASSWORD="${NONADMIN_PASSWORD:-viewer}"

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_dedup_mgmt_${timestamp}.db}"
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

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

log "Seed identity/meta (db=${DB_PATH})"
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
  --user-id 1 --roles admin >/dev/null
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$NONADMIN_USERNAME" --password "$NONADMIN_PASSWORD" \
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

request_upload() {
  local path="$1"
  local file_path="$2"
  local out_path="$3"

  local url="${BASE_URL}${path}"
  local http_code
  http_code="$(curl -sS -o "$out_path" -w "%{http_code}" -X POST "$url" "${auth_header[@]}" -F "file=@${file_path}")"
  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    cat "$out_path" >&2 || true
    fail "POST ${path} (upload) -> HTTP ${http_code} (out: ${out_path})"
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

assert_nonempty() {
  local label="$1"
  local val="$2"
  if [[ -z "$val" ]]; then
    fail "${label}: expected non-empty"
  fi
}

log "Login as non-admin and verify dedup endpoints are admin-only"
nonadmin_login_json="${OUT_DIR}/login_nonadmin.json"
code="$(
  curl -sS -o "$nonadmin_login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${NONADMIN_USERNAME}\",\"password\":\"${NONADMIN_PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$nonadmin_login_json" >&2 || true
  fail "non-admin login -> HTTP $code"
fi
NONADMIN_TOKEN="$("$PY_BIN" - "$nonadmin_login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
if [[ -z "$NONADMIN_TOKEN" ]]; then
  fail "failed to parse non-admin access_token"
fi

nonadmin_auth_header=(-H "Authorization: Bearer ${NONADMIN_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")
nonadmin_out="${OUT_DIR}/nonadmin_dedup_rules.json"
code="$(
  curl -sS -o "$nonadmin_out" -w "%{http_code}" \
    "${BASE_URL}/api/v1/dedup/rules" "${nonadmin_auth_header[@]}"
)"
assert_eq "non-admin GET /dedup/rules http_code" "$code" "403"

nonadmin_out="${OUT_DIR}/nonadmin_dedup_records.json"
code="$(
  curl -sS -o "$nonadmin_out" -w "%{http_code}" \
    "${BASE_URL}/api/v1/dedup/records?limit=1" "${nonadmin_auth_header[@]}"
)"
assert_eq "non-admin GET /dedup/records http_code" "$code" "403"

log "Create two Part items"
ts="$(date +%s)"

part_a_json="${OUT_DIR}/part_a.json"
request_json POST "/api/v1/aml/apply" "$part_a_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"DEDUP-MGMT-A-${ts}\",\"name\":\"Dedup Mgmt A ${ts}\"}}"
part_a_id="$(json_id "$part_a_json")"
assert_nonempty "part_a.id" "$part_a_id"

part_b_json="${OUT_DIR}/part_b.json"
request_json POST "/api/v1/aml/apply" "$part_b_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"DEDUP-MGMT-B-${ts}\",\"name\":\"Dedup Mgmt B ${ts}\"}}"
part_b_id="$(json_id "$part_b_json")"
assert_nonempty "part_b.id" "$part_b_id"

log "Upload and attach two files to the two Parts"
file_a_path="${OUT_DIR}/file_a.txt"
file_b_path="${OUT_DIR}/file_b.txt"
printf "dedup-mgmt-e2e file A %s\n" "$ts" >"$file_a_path"
printf "dedup-mgmt-e2e file B %s\n" "$ts" >"$file_b_path"

file_a_upload_json="${OUT_DIR}/file_a_upload.json"
request_upload "/api/v1/file/upload?generate_preview=false" "$file_a_path" "$file_a_upload_json"
file_a_id="$(json_get "$file_a_upload_json" id)"
assert_nonempty "file_a.id" "$file_a_id"

file_b_upload_json="${OUT_DIR}/file_b_upload.json"
request_upload "/api/v1/file/upload?generate_preview=false" "$file_b_path" "$file_b_upload_json"
file_b_id="$(json_get "$file_b_upload_json" id)"
assert_nonempty "file_b.id" "$file_b_id"

attach_a_json="${OUT_DIR}/attach_a.json"
request_json POST "/api/v1/file/attach" "$attach_a_json" \
  "{\"item_id\":\"${part_a_id}\",\"file_id\":\"${file_a_id}\",\"file_role\":\"attachment\",\"description\":\"dedup mgmt e2e\"}"

attach_b_json="${OUT_DIR}/attach_b.json"
request_json POST "/api/v1/file/attach" "$attach_b_json" \
  "{\"item_id\":\"${part_b_id}\",\"file_id\":\"${file_b_id}\",\"file_role\":\"attachment\",\"description\":\"dedup mgmt e2e\"}"

log "Create a Dedup rule (admin-only)"
rule_name="dedup-mgmt-e2e-${ts}"
rule_json="${OUT_DIR}/dedup_rule_create.json"
request_json POST "/api/v1/dedup/rules" "$rule_json" \
  "{\"name\":\"${rule_name}\",\"description\":\"Dedup management E2E rule\",\"priority\":10,\"is_active\":true}"
rule_id="$(json_get "$rule_json" id)"
assert_nonempty "dedup_rule.id" "$rule_id"

log "List rules and confirm created rule is present"
rules_list_json="${OUT_DIR}/dedup_rules_list.json"
request_json GET "/api/v1/dedup/rules" "$rules_list_json"
"$PY_BIN" - "$rules_list_json" "$rule_id" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  items = json.load(f)
rid = sys.argv[2]
if not any(isinstance(r, dict) and r.get("id") == rid for r in (items or [])):
  raise SystemExit("expected rule_id in list_rules response")
print("rules_list_contains_created=1")
PY

log "Get rule by id"
rule_get_json="${OUT_DIR}/dedup_rule_get.json"
request_json GET "/api/v1/dedup/rules/${rule_id}" "$rule_get_json"
assert_eq "get_rule.id" "$(json_get "$rule_get_json" id)" "$rule_id"

log "Create and run a Dedup batch (admin-only; API-level semantics only)"
batch_create_json="${OUT_DIR}/dedup_batch_create.json"
request_json POST "/api/v1/dedup/batches" "$batch_create_json" \
  "{\"name\":\"dedup-mgmt-batch-${ts}\",\"description\":\"Dedup batch (E2E)\",\"scope_type\":\"file_list\",\"scope_config\":{\"file_ids\":[\"${file_a_id}\",\"${file_b_id}\"]},\"rule_id\":\"${rule_id}\"}"
batch_id="$(json_get "$batch_create_json" id)"
assert_nonempty "dedup_batch.id" "$batch_id"

batch_list_json="${OUT_DIR}/dedup_batches_list.json"
request_json GET "/api/v1/dedup/batches?limit=10&offset=0" "$batch_list_json"
"$PY_BIN" - "$batch_list_json" "$batch_id" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
bid = sys.argv[2]
items = data.get("items") or []
if not any(isinstance(b, dict) and b.get("id") == bid for b in items):
  raise SystemExit("expected batch_id in list_batches response")
print("batches_list_contains_created=1")
PY

batch_get_json="${OUT_DIR}/dedup_batch_get.json"
request_json GET "/api/v1/dedup/batches/${batch_id}" "$batch_get_json"
assert_eq "batch.rule_id" "$(json_get "$batch_get_json" rule_id)" "$rule_id"

batch_run_json="${OUT_DIR}/dedup_batch_run.json"
request_json POST "/api/v1/dedup/batches/${batch_id}/run" "$batch_run_json" \
  "{\"mode\":\"fast\",\"limit\":1,\"priority\":30,\"dedupe\":true,\"index\":false}"
jobs_created="$(json_get "$batch_run_json" jobs_created)"
if [[ "${jobs_created:-0}" -lt 1 ]]; then
  cat "$batch_run_json" >&2 || true
  fail "expected jobs_created >= 1"
fi

batch_refresh_json="${OUT_DIR}/dedup_batch_refresh.json"
request_json POST "/api/v1/dedup/batches/${batch_id}/refresh" "$batch_refresh_json"
"$PY_BIN" - "$batch_refresh_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
summary = data.get("summary") or {}
job_status = summary.get("job_status") or {}
pending = int(job_status.get("pending") or 0)
assert pending >= 1, job_status
print("batch_refresh_job_status_ok=1")
PY

log "Inject one SimilarityRecord into SQLite (no create API by design)"
record_id="$("$PY_BIN" - <<'PY'
import uuid
print(str(uuid.uuid4()))
PY
)"
assert_nonempty "similarity_record.id" "$record_id"

pair_key=""
if [[ "$file_a_id" < "$file_b_id" ]]; then
  pair_key="${file_a_id}|${file_b_id}"
else
  pair_key="${file_b_id}|${file_a_id}"
fi

DB_PATH="$DB_PATH" REC_ID="$record_id" SRC_FILE_ID="$file_a_id" TGT_FILE_ID="$file_b_id" PAIR_KEY="$pair_key" RULE_ID="$rule_id" \
  "$PY_BIN" - <<'PY'
import datetime
import json
import os
import sqlite3

db_path = os.environ["DB_PATH"]
rec_id = os.environ["REC_ID"]
src = os.environ["SRC_FILE_ID"]
tgt = os.environ["TGT_FILE_ID"]
pair_key = os.environ["PAIR_KEY"]
rule_id = os.environ["RULE_ID"]

created_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
params = json.dumps({"rule_id": rule_id, "source": "verify_dedup_management.sh"})

conn = sqlite3.connect(db_path)
try:
  conn.execute("PRAGMA foreign_keys=ON")
  cur = conn.cursor()
  cur.execute(
    """
    INSERT INTO meta_similarity_records
      (id, source_file_id, target_file_id, pair_key, similarity_score, detection_params, status, created_at)
    VALUES
      (?,  ?,             ?,             ?,        ?,               ?,               ?,      ?)
    """,
    (rec_id, src, tgt, pair_key, 0.95, params, "pending", created_at),
  )
  conn.commit()
finally:
  conn.close()
print("inserted_similarity_record=1")
PY

log "List records (admin-only) and confirm injected record is present"
records_list_json="${OUT_DIR}/dedup_records_list.json"
request_json GET "/api/v1/dedup/records?limit=10&offset=0" "$records_list_json"
"$PY_BIN" - "$records_list_json" "$record_id" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
rid = sys.argv[2]
assert int(data.get("total") or 0) >= 1, "expected total>=1"
items = data.get("items") or []
if not any(isinstance(r, dict) and r.get("id") == rid for r in items):
  raise SystemExit("expected record_id in list_records response")
print("records_list_contains_injected=1")
PY

log "Get record by id (pending)"
record_get_json="${OUT_DIR}/dedup_record_get.json"
request_json GET "/api/v1/dedup/records/${record_id}" "$record_get_json"
assert_eq "record.status (before review)" "$(json_get "$record_get_json" status)" "pending"

log "Review record -> confirmed (create Part Equivalent relationship)"
review_json="${OUT_DIR}/dedup_record_review.json"
request_json POST "/api/v1/dedup/records/${record_id}/review" "$review_json" \
  "{\"status\":\"confirmed\",\"comment\":\"E2E confirm\",\"create_relationship\":true}"
assert_eq "record.status (after review)" "$(json_get "$review_json" status)" "confirmed"
relationship_item_id="$(json_get "$review_json" relationship_item_id)"
assert_nonempty "record.relationship_item_id" "$relationship_item_id"

log "Verify relationship item exists in DB and is type 'Part Equivalent'"
DB_PATH="$DB_PATH" REL_ID="$relationship_item_id" "$PY_BIN" - <<'PY'
import os
import sqlite3

db_path = os.environ["DB_PATH"]
rel_id = os.environ["REL_ID"]

conn = sqlite3.connect(db_path)
try:
  cur = conn.cursor()
  cur.execute("SELECT item_type_id FROM meta_items WHERE id = ?", (rel_id,))
  row = cur.fetchone()
  if not row:
    raise SystemExit("expected relationship item in meta_items")
  if row[0] != "Part Equivalent":
    raise SystemExit(f"expected item_type_id='Part Equivalent', got {row[0]!r}")
  print("relationship_item_type_ok=1")
finally:
  conn.close()
PY

log "Dedup report (rule_id filter) should count 1 confirmed record"
report_json="${OUT_DIR}/dedup_report.json"
request_json GET "/api/v1/dedup/report?days=30&rule_id=${rule_id}&latest_limit=5" "$report_json"
assert_eq "report.total" "$(json_get "$report_json" total)" "1"
confirmed_count="$("$PY_BIN" - "$report_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
print((data.get("by_status") or {}).get("confirmed", 0))
PY
)"
assert_eq "report.by_status.confirmed" "$confirmed_count" "1"

rule_count="$("$PY_BIN" - "$report_json" "$rule_id" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
rid = sys.argv[2]
print((data.get("by_rule_id") or {}).get(rid, 0))
PY
)"
assert_eq "report.by_rule_id[rule_id]" "$rule_count" "1"

log "Dedup report export (CSV)"
csv_path="${OUT_DIR}/dedup_report.csv"
request_raw GET "/api/v1/dedup/report/export?days=30&rule_id=${rule_id}&limit=100" "$csv_path"

header="$(head -n 1 "$csv_path" | tr -d '\r' || true)"
assert_eq "csv.header" "$header" "id,status,source_file_id,target_file_id,pair_key,similarity_score,rule_id,batch_id,reviewed_by_id,reviewed_at,relationship_item_id,created_at"
grep -q "$record_id" "$csv_path" || fail "csv does not contain record_id"

log "PASS: Dedup management E2E verification"
