#!/usr/bin/env bash
set -euo pipefail

# Self-contained perf smoke for e-sign endpoints.
#
# Coverage:
# - POST /api/v1/esign/sign
# - POST /api/v1/esign/verify/{signature_id}
# - GET  /api/v1/esign/audit-summary
#
# The script starts a temporary local server backed by an isolated SQLite DB,
# executes several timing samples, and asserts p95 latency thresholds.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-esign-perf/${timestamp}"
OUT_DIR="${OUT_DIR:-$OUT_DIR_DEFAULT}"
mkdir -p "$OUT_DIR"

SAMPLES="${PERF_ESIGN_SAMPLES:-5}"
SIGN_MAX_MS="${PERF_ESIGN_SIGN_MAX_MS:-1500}"
VERIFY_MAX_MS="${PERF_ESIGN_VERIFY_MAX_MS:-1300}"
AUDIT_SUMMARY_MAX_MS="${PERF_ESIGN_AUDIT_SUMMARY_MAX_MS:-1200}"

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
  PORT="$($PY_BIN - <<'PY'
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_esign_perf_${timestamp}.db}"
db_path_norm="${DB_PATH#/}"

export PYTHONPATH="${PYTHONPATH:-src}"
export YUANTUS_TENANCY_MODE="single"
export YUANTUS_SCHEMA_MODE="create_all"
export YUANTUS_DATABASE_URL="sqlite:////${db_path_norm}"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:////${db_path_norm}"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

sign_ms_file="${OUT_DIR}/sign_ms.txt"
verify_ms_file="${OUT_DIR}/verify_ms.txt"
audit_summary_ms_file="${OUT_DIR}/audit_summary_ms.txt"
: > "$sign_ms_file"
: > "$verify_ms_file"
: > "$audit_summary_ms_file"

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

TOKEN="$($PY_BIN - "$login_json" <<'PY'
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

timed_request_json() {
  local method="$1"
  local path="$2"
  local out_path="$3"
  local time_out_path="$4"
  local data="${5:-}"

  local url="${BASE_URL}${path}"
  local meta
  if [[ -n "$data" ]]; then
    meta="$(curl -sS -o "$out_path" -w "%{http_code} %{time_total}" -X "$method" "$url" "${auth_header[@]}" "${json_header[@]}" -d "$data")"
  else
    meta="$(curl -sS -o "$out_path" -w "%{http_code} %{time_total}" -X "$method" "$url" "${auth_header[@]}")"
  fi

  local http_code="${meta%% *}"
  local time_total="${meta#* }"

  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    cat "$out_path" >&2 || true
    fail "${method} ${path} -> HTTP ${http_code}"
  fi

  "$PY_BIN" - "$time_total" "$time_out_path" <<'PY'
import sys
seconds = float(sys.argv[1])
out_path = sys.argv[2]
ms = seconds * 1000.0
with open(out_path, "a", encoding="utf-8") as f:
  f.write(f"{ms:.3f}\n")
print(f"{ms:.3f}")
PY
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

assert_p95_under() {
  local label="$1"
  local ms_file="$2"
  local max_ms="$3"
  local out_json="$4"

  "$PY_BIN" - "$label" "$ms_file" "$max_ms" "$out_json" <<'PY'
import json
import math
import statistics
import sys

label = sys.argv[1]
path = sys.argv[2]
threshold = float(sys.argv[3])
out_json = sys.argv[4]
values = []
with open(path, "r", encoding="utf-8") as f:
    for raw in f:
        s = raw.strip()
        if s:
            values.append(float(s))
if not values:
    raise SystemExit(f"{label}: no samples")

sorted_vals = sorted(values)
idx = max(0, min(len(sorted_vals) - 1, int(math.ceil(0.95 * len(sorted_vals))) - 1))
p95 = sorted_vals[idx]
p50 = statistics.median(values)

payload = {
    "label": label,
    "samples": len(values),
    "threshold_ms": threshold,
    "p50_ms": round(p50, 3),
    "p95_ms": round(p95, 3),
    "values_ms": values,
}
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)

print(f"{label}: samples={len(values)} p50={p50:.3f}ms p95={p95:.3f}ms threshold={threshold:.3f}ms")
if p95 > threshold:
    raise SystemExit(f"{label}: p95 {p95:.3f}ms exceeds threshold {threshold:.3f}ms")
PY
}

ts="$(date +%s)"
reason_json="${OUT_DIR}/reason_create.json"
log "Create signing reason fixture"
request_json POST "/api/v1/esign/reasons" "$reason_json" \
  "{\"code\":\"PERF-ESIGN-${ts}\",\"name\":\"Perf E-sign Reason\",\"meaning\":\"approved\",\"requires_password\":true,\"requires_comment\":false,\"sequence\":10}"
reason_id="$(json_id "$reason_json")"
[[ -n "$reason_id" ]] || fail "failed to parse reason id"

last_item_id=""
log "Run timed sign+verify samples (count=${SAMPLES})"
for i in $(seq 1 "$SAMPLES"); do
  item_number="ESIGN-PERF-${ts}-${i}"
  item_json="${OUT_DIR}/item_${i}.json"
  request_json POST "/api/v1/aml/apply" "$item_json" \
    "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${item_number}\",\"name\":\"E-sign Perf ${i}\"}}"
  item_id="$(json_id "$item_json")"
  [[ -n "$item_id" ]] || fail "failed to parse item id"
  last_item_id="$item_id"

  request_json POST "/api/v1/esign/manifests" "${OUT_DIR}/manifest_${i}.json" \
    "{\"item_id\":\"${item_id}\",\"generation\":1,\"required_signatures\":[{\"meaning\":\"approved\",\"role\":\"admin\",\"required\":true}]}"

  sign_out="${OUT_DIR}/sign_${i}.json"
  sign_ms="$(timed_request_json POST "/api/v1/esign/sign" "$sign_out" "$sign_ms_file" "{\"item_id\":\"${item_id}\",\"meaning\":\"approved\",\"password\":\"${PASSWORD}\",\"reason_id\":\"${reason_id}\",\"comment\":\"perf\"}")"
  signature_id="$(json_id "$sign_out")"
  [[ -n "$signature_id" ]] || fail "failed to parse signature id"

  verify_out="${OUT_DIR}/verify_${i}.json"
  verify_ms="$(timed_request_json POST "/api/v1/esign/verify/${signature_id}" "$verify_out" "$verify_ms_file")"

  "$PY_BIN" - "$verify_out" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)
if not isinstance(data.get("is_valid"), bool):
    raise SystemExit("verify response missing is_valid")
if not data.get("signature"):
    raise SystemExit("verify response missing signature block")
PY

  log "sample#${i}: sign=${sign_ms}ms verify=${verify_ms}ms"
done

log "Run timed audit-summary samples (count=${SAMPLES})"
for i in $(seq 1 "$SAMPLES"); do
  audit_out="${OUT_DIR}/audit_summary_${i}.json"
  audit_ms="$(timed_request_json GET "/api/v1/esign/audit-summary?item_id=${last_item_id}" "$audit_out" "$audit_summary_ms_file")"

  "$PY_BIN" - "$audit_out" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)
if not isinstance(data, dict):
    raise SystemExit("audit-summary must return an object")
if "total" not in data:
    raise SystemExit("audit-summary missing total")
PY

  log "audit-sample#${i}: audit_summary=${audit_ms}ms"
done

metrics_sign_json="${OUT_DIR}/metrics_sign.json"
metrics_verify_json="${OUT_DIR}/metrics_verify.json"
metrics_audit_summary_json="${OUT_DIR}/metrics_audit_summary.json"

assert_p95_under "esign.sign" "$sign_ms_file" "$SIGN_MAX_MS" "$metrics_sign_json"
assert_p95_under "esign.verify" "$verify_ms_file" "$VERIFY_MAX_MS" "$metrics_verify_json"
assert_p95_under "esign.audit_summary" "$audit_summary_ms_file" "$AUDIT_SUMMARY_MAX_MS" "$metrics_audit_summary_json"

"$PY_BIN" - "$metrics_sign_json" "$metrics_verify_json" "$metrics_audit_summary_json" "${OUT_DIR}/metrics_summary.json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    sign = json.load(f)
with open(sys.argv[2], "r", encoding="utf-8") as f:
    verify = json.load(f)
with open(sys.argv[3], "r", encoding="utf-8") as f:
    audit = json.load(f)

payload = {
    "esign": {
        "sign": sign,
        "verify": verify,
        "audit_summary": audit,
    }
}
with open(sys.argv[4], "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
print("metrics_summary: OK")
PY

log "ALL CHECKS PASSED out=${OUT_DIR}"
