#!/usr/bin/env bash
# =============================================================================
# S7 Quota Verification Script
# =============================================================================
# Validates tenant quota enforcement for users/orgs/files/jobs.
# Requires YUANTUS_QUOTA_MODE=enforce on the running server.
# =============================================================================
set -euo pipefail

BASE="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
VERIFY_QUOTA_MONITORING="${VERIFY_QUOTA_MONITORING:-0}"

PLATFORM_TENANT="${PLATFORM_TENANT:-platform}"
PLATFORM_ORG="${PLATFORM_ORG:-platform}"
PLATFORM_USER="${PLATFORM_USER:-platform-admin}"
PLATFORM_PASSWORD="${PLATFORM_PASSWORD:-platform-admin}"
PLATFORM_USER_ID="${PLATFORM_USER_ID:-9001}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

TS="$(date +%s)"
FAILED=0

fail() {
  echo "FAIL: $1" >&2
  FAILED=1
}

echo "==> Seed identity + meta"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null

echo "==> Login as admin"
ADMIN_TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"

echo "==> Read current quota usage"
QUOTA_JSON="$(
  curl -s "$BASE/api/v1/admin/quota" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
MODE="$("$PY" -c 'import sys,json;print(json.load(sys.stdin).get("mode",""))' <<<"$QUOTA_JSON")"

if [[ "$MODE" != "enforce" ]]; then
  echo "SKIP: quota mode is '$MODE' (expected enforce)"
  exit 0
fi

if [[ "$VERIFY_QUOTA_MONITORING" == "1" ]]; then
  echo "==> Platform admin quota monitoring"
  "$CLI" seed-identity \
    --tenant "$PLATFORM_TENANT" \
    --org "$PLATFORM_ORG" \
    --username "$PLATFORM_USER" \
    --password "$PLATFORM_PASSWORD" \
    --user-id "$PLATFORM_USER_ID" \
    --roles admin \
    --superuser >/dev/null

  PLATFORM_TOKEN="$(
    curl -s -X POST "$BASE/api/v1/auth/login" \
      -H 'content-type: application/json' \
      -d "{\"tenant_id\":\"$PLATFORM_TENANT\",\"username\":\"$PLATFORM_USER\",\"password\":\"$PLATFORM_PASSWORD\"}" \
      | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
  )"
  if [[ -z "$PLATFORM_TOKEN" ]]; then
    fail "Platform admin login failed"
  fi

  QUOTAS_RAW="$(
    curl -s -w 'HTTPSTATUS:%{http_code}' \
      "$BASE/api/v1/admin/tenants/quotas" \
      -H "Authorization: Bearer $PLATFORM_TOKEN" \
      -H "x-tenant-id: $PLATFORM_TENANT"
  )"
  QUOTAS_BODY="${QUOTAS_RAW%HTTPSTATUS:*}"
  QUOTAS_STATUS="${QUOTAS_RAW##*HTTPSTATUS:}"
  if [[ "$QUOTAS_STATUS" == "403" && "$QUOTAS_BODY" == *"Platform admin disabled"* ]]; then
    echo "SKIP: platform admin disabled"
  elif [[ "$QUOTAS_STATUS" != "200" ]]; then
    echo "Response: $QUOTAS_BODY" >&2
    fail "Expected /admin/tenants/quotas to succeed, got HTTP $QUOTAS_STATUS"
  else
    TENANT="$TENANT" QUOTAS_JSON="$QUOTAS_BODY" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("QUOTAS_JSON", "")
tenant = os.environ.get("TENANT", "")
if not raw:
    raise SystemExit("Empty response from /admin/tenants/quotas")

data = json.loads(raw)
items = data.get("items") or []
if not items:
    raise SystemExit("Expected items list in /admin/tenants/quotas")

match = [item for item in items if item.get("tenant_id") == tenant]
if not match:
    raise SystemExit(f"Missing tenant {tenant} in /admin/tenants/quotas")

required = {"mode", "quota", "usage"}
for key in required:
    if key not in match[0]:
        raise SystemExit(f"Missing {key} in tenant quota summary")
print("Quota monitoring: OK")
PY
  fi
fi

ORIG_QUOTA_JSON="$("$PY" -c 'import sys,json;print(json.dumps(json.load(sys.stdin).get("quota") or {}))' <<<"$QUOTA_JSON")"
RESTORE_JSON="${QUOTA_RESTORE_JSON:-$ORIG_QUOTA_JSON}"

restore_quota() {
  if [[ -n "$RESTORE_JSON" ]]; then
    curl -s -o /tmp/quota_restore.json -w '%{http_code}' \
      -X PUT "$BASE/api/v1/admin/quota" \
      -H 'content-type: application/json' \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
      -d "$RESTORE_JSON" >/dev/null
  fi
}

trap restore_quota EXIT

USERS="$("$PY" -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("users"))' <<<"$QUOTA_JSON")"
ORGS="$("$PY" -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("orgs"))' <<<"$QUOTA_JSON")"
FILES="$("$PY" -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("files"))' <<<"$QUOTA_JSON")"
BYTES="$("$PY" -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("storage_bytes"))' <<<"$QUOTA_JSON")"
JOBS="$("$PY" -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("active_jobs"))' <<<"$QUOTA_JSON")"

if [[ -z "$USERS" || -z "$ORGS" || -z "$FILES" || -z "$BYTES" || -z "$JOBS" ]]; then
  fail "Missing usage fields from /admin/quota"
fi

TMP_FILE="$(mktemp)"
printf "quota-test-%s" "$TS" > "$TMP_FILE"
FILE_SIZE="$(wc -c < "$TMP_FILE" | tr -d ' ')"

MAX_USERS=$((USERS + 1))
MAX_ORGS=$((ORGS + 1))
MAX_FILES=$((FILES + 1))
MAX_BYTES=$((BYTES + FILE_SIZE))
MAX_JOBS=$((JOBS + 1))

echo "==> Update quota limits"
HTTP_CODE="$(curl -s -o /tmp/quota_update.json -w '%{http_code}' \
  -X PUT "$BASE/api/v1/admin/quota" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"max_users\":$MAX_USERS,\"max_orgs\":$MAX_ORGS,\"max_files\":$MAX_FILES,\"max_storage_bytes\":$MAX_BYTES,\"max_active_jobs\":$MAX_JOBS}"
)"
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "Failed to update quotas: HTTP $HTTP_CODE"
fi

echo "==> Org quota enforcement"
ORG1="org-q-$TS"
HTTP_CODE="$(curl -s -o /tmp/org_create.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/admin/orgs" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"id\":\"$ORG1\",\"name\":\"Quota Org 1\"}"
)"
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "Expected org create to succeed, got HTTP $HTTP_CODE"
fi

ORG2="org-q-$TS-2"
HTTP_CODE="$(curl -s -o /tmp/org_create2.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/admin/orgs" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"id\":\"$ORG2\",\"name\":\"Quota Org 2\"}"
)"
if [[ "$HTTP_CODE" != "429" ]]; then
  fail "Expected org quota to block second org, got HTTP $HTTP_CODE"
fi

echo "==> User quota enforcement"
USER1="user-q-$TS"
HTTP_CODE="$(curl -s -o /tmp/user_create.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/admin/users" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"username\":\"$USER1\",\"password\":\"$USER1\"}"
)"
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "Expected user create to succeed, got HTTP $HTTP_CODE"
fi

USER2="user-q-$TS-2"
HTTP_CODE="$(curl -s -o /tmp/user_create2.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/admin/users" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"username\":\"$USER2\",\"password\":\"$USER2\"}"
)"
if [[ "$HTTP_CODE" != "429" ]]; then
  fail "Expected user quota to block second user, got HTTP $HTTP_CODE"
fi

echo "==> File quota enforcement"
HTTP_CODE="$(curl -s -o /tmp/file_upload.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/file/upload" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -F "file=@${TMP_FILE}"
)"
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "Expected file upload to succeed, got HTTP $HTTP_CODE"
fi

printf "quota-test-2-%s" "$TS" > "$TMP_FILE"
HTTP_CODE="$(curl -s -o /tmp/file_upload2.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/file/upload" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -F "file=@${TMP_FILE}"
)"
if [[ "$HTTP_CODE" != "429" ]]; then
  fail "Expected file quota to block second upload, got HTTP $HTTP_CODE"
fi

echo "==> Job quota enforcement"
HTTP_CODE="$(curl -s -o /tmp/job_create.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/jobs" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"task_type\":\"quota_test\",\"payload\":{\"ts\":\"$TS\"},\"dedupe\":false}"
)"
if [[ "$HTTP_CODE" != "200" ]]; then
  fail "Expected job create to succeed, got HTTP $HTTP_CODE"
fi

HTTP_CODE="$(curl -s -o /tmp/job_create2.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/jobs" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"task_type\":\"quota_test\",\"payload\":{\"ts\":\"${TS}-2\"},\"dedupe\":false}"
)"
if [[ "$HTTP_CODE" != "429" ]]; then
  fail "Expected job quota to block second job, got HTTP $HTTP_CODE"
fi

rm -f "$TMP_FILE"

if [[ "$FAILED" -ne 0 ]]; then
  exit 1
fi

echo "ALL CHECKS PASSED"
