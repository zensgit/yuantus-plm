#!/usr/bin/env bash
set -euo pipefail

# Self-contained perf smoke for reports endpoints.
#
# Coverage:
# - POST /api/v1/reports/search
# - GET  /api/v1/reports/summary
# - POST /api/v1/reports/definitions/{id}/export
#
# The script starts a temporary local server backed by an isolated SQLite DB,
# executes several timing samples, and asserts p95 latency thresholds.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-reports-perf/${timestamp}"
OUT_DIR="${OUT_DIR:-$OUT_DIR_DEFAULT}"
mkdir -p "$OUT_DIR"

SAMPLES="${PERF_REPORTS_SAMPLES:-5}"
SEARCH_MAX_MS="${PERF_REPORTS_SEARCH_MAX_MS:-1600}"
SUMMARY_MAX_MS="${PERF_REPORTS_SUMMARY_MAX_MS:-1000}"
EXPORT_MAX_MS="${PERF_REPORTS_EXPORT_MAX_MS:-2000}"
PART_COUNT="${PERF_REPORTS_PART_COUNT:-30}"

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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_reports_perf_${timestamp}.db}"
db_path_norm="${DB_PATH#/}"

export PYTHONPATH="${PYTHONPATH:-src}"
export YUANTUS_TENANCY_MODE="single"
export YUANTUS_SCHEMA_MODE="create_all"
export YUANTUS_DATABASE_URL="sqlite:////${db_path_norm}"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:////${db_path_norm}"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

search_ms_file="${OUT_DIR}/search_ms.txt"
summary_ms_file="${OUT_DIR}/summary_ms.txt"
export_ms_file="${OUT_DIR}/export_ms.txt"
: > "$search_ms_file"
: > "$summary_ms_file"
: > "$export_ms_file"

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
fulltext="RPT-PERF-${ts}"

log "Create fixture items (count=${PART_COUNT})"
for i in $(seq 1 "$PART_COUNT"); do
  part_out="${OUT_DIR}/part_${i}.json"
  request_json POST "/api/v1/aml/apply" "$part_out" \
    "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${fulltext}-${i}\",\"name\":\"Reports Perf ${ts} ${i}\",\"description\":\"${fulltext}\"}}"
done

log "Create report definition fixture"
report_create_json="${OUT_DIR}/report_create.json"
request_json POST "/api/v1/reports/definitions" "$report_create_json" \
  "{\"name\":\"Reports Perf ${ts}\",\"code\":\"RPT-PERF-${ts}\",\"description\":\"perf smoke\",\"category\":\"perf\",\"report_type\":\"table\",\"data_source\":{\"type\":\"query\",\"item_type_id\":\"Part\",\"full_text\":\"${fulltext}\"},\"is_public\":false,\"is_active\":true}"
report_id="$(json_id "$report_create_json")"
[[ -n "$report_id" ]] || fail "failed to parse report id"

log "Run timed samples (count=${SAMPLES})"
for i in $(seq 1 "$SAMPLES"); do
  search_out="${OUT_DIR}/search_${i}.json"
  search_ms="$(timed_request_json POST "/api/v1/reports/search" "$search_out" "$search_ms_file" "{\"item_type_id\":\"Part\",\"full_text\":\"${fulltext}\",\"page\":1,\"page_size\":20,\"include_count\":true}")"

  summary_out="${OUT_DIR}/summary_${i}.json"
  summary_ms="$(timed_request_json GET "/api/v1/reports/summary" "$summary_out" "$summary_ms_file")"

  export_out="${OUT_DIR}/export_${i}.csv"
  export_ms="$(timed_request_json POST "/api/v1/reports/definitions/${report_id}/export" "$export_out" "$export_ms_file" '{"export_format":"csv","page":1,"page_size":500}')"

  "$PY_BIN" - "$search_out" "$summary_out" "$export_out" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    search = json.load(f)
with open(sys.argv[2], "r", encoding="utf-8") as f:
    summary = json.load(f)

if not isinstance(search.get("items") or [], list):
    raise SystemExit("reports/search items must be a list")
if int(search.get("total") or 0) < 1:
    raise SystemExit("reports/search total should be >= 1")
meta = summary.get("meta") or {}
if not meta.get("tenant_id"):
    raise SystemExit("reports/summary meta.tenant_id missing")

csv_text = open(sys.argv[3], "r", encoding="utf-8", errors="replace").read()
if not csv_text.strip():
    raise SystemExit("reports export returned empty content")
if "id" not in csv_text.splitlines()[0].lower():
    raise SystemExit("reports export missing csv header")
PY

  log "sample#${i}: search=${search_ms}ms summary=${summary_ms}ms export=${export_ms}ms"
done

# Best-effort cleanup.
request_json DELETE "/api/v1/reports/definitions/${report_id}" "${OUT_DIR}/report_delete.json"

metrics_search_json="${OUT_DIR}/metrics_search.json"
metrics_summary_json="${OUT_DIR}/metrics_summary_endpoint.json"
metrics_export_json="${OUT_DIR}/metrics_export.json"

assert_p95_under "reports.search" "$search_ms_file" "$SEARCH_MAX_MS" "$metrics_search_json"
assert_p95_under "reports.summary" "$summary_ms_file" "$SUMMARY_MAX_MS" "$metrics_summary_json"
assert_p95_under "reports.export" "$export_ms_file" "$EXPORT_MAX_MS" "$metrics_export_json"

"$PY_BIN" - "$metrics_search_json" "$metrics_summary_json" "$metrics_export_json" "${OUT_DIR}/metrics_summary.json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    search = json.load(f)
with open(sys.argv[2], "r", encoding="utf-8") as f:
    summary = json.load(f)
with open(sys.argv[3], "r", encoding="utf-8") as f:
    export = json.load(f)

payload = {
    "reports": {
        "search": search,
        "summary": summary,
        "export": export,
    }
}
with open(sys.argv[4], "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
print("metrics_summary: OK")
PY

log "ALL CHECKS PASSED out=${OUT_DIR}"
