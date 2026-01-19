#!/usr/bin/env bash
# =============================================================================
# Reports Summary Verification Script
# Verifies /reports/summary returns expected aggregates.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
DB_URL="${DB_URL:-}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$DB_URL" || -n "$identity_url" ]]; then
    env \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

echo "=============================================="
echo "Reports Summary Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login as admin"
ADMIN_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

TS="$(date +%s)"

echo ""
echo "==> Create Part item"
ITEM_NUMBER="REPORT-$TS"
ITEM_ID="$(
  $CURL -X POST "$API/aml/apply" \
    -H 'content-type: application/json' \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$ITEM_NUMBER\",\"name\":\"Report Item $TS\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$ITEM_ID" ]]; then
  fail "Failed to create Part item"
fi
ok "Created Part: $ITEM_ID"

echo ""
echo "==> Upload file"
TMP_FILE="/tmp/yuantus_report_summary_$TS.txt"
echo "report summary $TS" > "$TMP_FILE"
FILE_ID="$(
  $CURL -X POST "$API/file/upload" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$TMP_FILE;filename=report_summary_$TS.txt" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$FILE_ID" ]]; then
  fail "Failed to upload file"
fi
ok "Uploaded file: $FILE_ID"

echo ""
echo "==> Create ECO stage + ECO"
STAGE_ID="$(
  $CURL -X POST "$API/eco/stages" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"REPORT-$TS\",\"sequence\":10,\"approval_type\":\"none\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$STAGE_ID" ]]; then
  fail "Failed to create ECO stage"
fi
ECO_ID="$(
  $CURL -X POST "$API/eco" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"ECO-REPORT-$TS\",\"eco_type\":\"bom\",\"product_id\":\"$ITEM_ID\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$ECO_ID" ]]; then
  fail "Failed to create ECO"
fi
ok "Created ECO: $ECO_ID"

echo ""
echo "==> Create job"
JOB_ID="$(
  $CURL -X POST "$API/jobs" \
    -H 'content-type: application/json' \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -d "{\"task_type\":\"cad_conversion\",\"payload\":{\"input_file_path\":\"report.dwg\"},\"priority\":5}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$JOB_ID" ]]; then
  fail "Failed to create job"
fi
ok "Created job: $JOB_ID"

echo ""
echo "==> Fetch reports summary"
SUMMARY="$($CURL "$API/reports/summary" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
TENANT="$TENANT" ORG="$ORG" RESP_JSON="$SUMMARY" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("RESP_JSON", "{}")
data = json.loads(raw)
tenant = os.environ.get("TENANT", "")
org = os.environ.get("ORG", "")

meta = data.get("meta") or {}
if meta.get("tenant_id") != tenant:
    raise SystemExit("meta.tenant_id mismatch")
if meta.get("org_id") != org:
    raise SystemExit("meta.org_id mismatch")
if not meta.get("tenancy_mode"):
    raise SystemExit("meta.tenancy_mode missing")
if not meta.get("generated_at"):
    raise SystemExit("meta.generated_at missing")

items = data.get("items") or {}
if items.get("total", 0) < 1:
    raise SystemExit("items.total should be >= 1")
by_type = items.get("by_type") or []
if not any(r.get("item_type_id") == "Part" and r.get("count", 0) >= 1 for r in by_type):
    raise SystemExit("items.by_type should include Part")

files = data.get("files") or {}
if files.get("total", 0) < 1:
    raise SystemExit("files.total should be >= 1")
by_doc = files.get("by_document_type") or []
if not any(r.get("document_type") == "other" and r.get("count", 0) >= 1 for r in by_doc):
    raise SystemExit("files.by_document_type should include other")

ecos = data.get("ecos") or {}
if ecos.get("total", 0) < 1:
    raise SystemExit("ecos.total should be >= 1")
by_state = ecos.get("by_state") or []
if not any(r.get("state") == "draft" and r.get("count", 0) >= 1 for r in by_state):
    raise SystemExit("ecos.by_state should include draft")

jobs = data.get("jobs") or {}
if jobs.get("total", 0) < 1:
    raise SystemExit("jobs.total should be >= 1")
by_status = jobs.get("by_status") or []
if not any(r.get("status") == "pending" and r.get("count", 0) >= 1 for r in by_status):
    raise SystemExit("jobs.by_status should include pending")

print("Summary checks: OK")
PY
ok "Summary checks passed"

echo ""
echo "=============================================="
echo "Reports Summary Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
