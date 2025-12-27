#!/usr/bin/env bash
# =============================================================================
# Tenant Provisioning Verification Script
# Verifies platform admin tenant/org provisioning via /api/v1/admin.
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

TS="$(date +%s)"
NEW_TENANT="tenant-provision-$TS"
NEW_ORG="org-provision-$TS"
NEW_ADMIN="admin-$TS"
NEW_PASSWORD="admin-$TS"
EXTRA_ORG="org-extra-$TS"

if [[ -z "$DB_URL" && -n "${YUANTUS_DATABASE_URL:-}" ]]; then
  DB_URL="${YUANTUS_DATABASE_URL}"
fi

if [[ -z "$IDENTITY_DB_URL" && -n "${YUANTUS_IDENTITY_DATABASE_URL:-}" ]]; then
  IDENTITY_DB_URL="${YUANTUS_IDENTITY_DATABASE_URL}"
fi

echo "=============================================="
echo "Tenant Provisioning Verification"
echo "BASE_URL: $BASE_URL"
echo "PLATFORM_TENANT: $PLATFORM_TENANT"
echo "NEW_TENANT: $NEW_TENANT"
echo "=============================================="

echo ""
echo "==> Seed platform admin identity"
run_cli seed-identity \
  --tenant "$PLATFORM_TENANT" \
  --org "$PLATFORM_ORG" \
  --username "$PLATFORM_USER" \
  --password "$PLATFORM_PASSWORD" \
  --user-id "$PLATFORM_USER_ID" \
  --roles admin \
  --superuser >/dev/null
ok "Platform admin seeded"

echo ""
echo "==> Login as platform admin"
PLATFORM_TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$PLATFORM_TENANT\",\"username\":\"$PLATFORM_USER\",\"password\":\"$PLATFORM_PASSWORD\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$PLATFORM_TOKEN" ]]; then
  fail "Platform admin login failed"
fi
ok "Platform admin login"

PLATFORM_HEADERS=(-H "Authorization: Bearer $PLATFORM_TOKEN" -H "x-tenant-id: $PLATFORM_TENANT")

echo ""
echo "==> Check platform admin access"
LIST_RAW="$($CURL -w 'HTTPSTATUS:%{http_code}' "$API/admin/tenants" "${PLATFORM_HEADERS[@]}")"
LIST_BODY="${LIST_RAW%HTTPSTATUS:*}"
LIST_STATUS="${LIST_RAW##*HTTPSTATUS:}"
if [[ "$LIST_STATUS" == "403" && "$LIST_BODY" == *"Platform admin disabled"* ]]; then
  echo "SKIP: platform admin disabled"
  exit 0
fi
if [[ "$LIST_STATUS" != "200" ]]; then
  echo "Response: $LIST_BODY" >&2
  fail "Platform admin access failed (status=$LIST_STATUS)"
fi
ok "Platform admin access OK"

echo ""
echo "==> Verify non-platform admin is blocked"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
USER_TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$USER_TOKEN" ]]; then
  fail "Tenant admin login failed"
fi
NON_PLATFORM_RAW="$($CURL -w 'HTTPSTATUS:%{http_code}' "$API/admin/tenants" \
  -H "Authorization: Bearer $USER_TOKEN" -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")"
NON_PLATFORM_STATUS="${NON_PLATFORM_RAW##*HTTPSTATUS:}"
if [[ "$NON_PLATFORM_STATUS" != "403" ]]; then
  fail "Expected 403 for non-platform admin, got $NON_PLATFORM_STATUS"
fi
ok "Non-platform admin blocked"

echo ""
echo "==> Create tenant with default org + admin"
CREATE_BODY="{\"id\":\"$NEW_TENANT\",\"name\":\"$NEW_TENANT\",\"create_default_org\":true,\"default_org_id\":\"$NEW_ORG\",\"admin_username\":\"$NEW_ADMIN\",\"admin_password\":\"$NEW_PASSWORD\",\"admin_email\":\"$NEW_ADMIN@example.com\"}"
CREATE_RAW="$($CURL -w 'HTTPSTATUS:%{http_code}' -X POST "$API/admin/tenants" \
  -H 'content-type: application/json' \
  "${PLATFORM_HEADERS[@]}" \
  -d "$CREATE_BODY")"
CREATE_BODY_RESP="${CREATE_RAW%HTTPSTATUS:*}"
CREATE_STATUS="${CREATE_RAW##*HTTPSTATUS:}"
if [[ "$CREATE_STATUS" != "200" ]]; then
  echo "Response: $CREATE_BODY_RESP" >&2
  fail "Tenant create failed (status=$CREATE_STATUS)"
fi
ok "Tenant created: $NEW_TENANT"

echo ""
echo "==> Get tenant"
GET_RAW="$($CURL -w 'HTTPSTATUS:%{http_code}' "$API/admin/tenants/$NEW_TENANT" "${PLATFORM_HEADERS[@]}")"
GET_BODY="${GET_RAW%HTTPSTATUS:*}"
GET_STATUS="${GET_RAW##*HTTPSTATUS:}"
if [[ "$GET_STATUS" != "200" ]]; then
  echo "Response: $GET_BODY" >&2
  fail "Get tenant failed (status=$GET_STATUS)"
fi
ok "Tenant fetched"

echo ""
echo "==> Create extra org for tenant"
ORG_RAW="$($CURL -w 'HTTPSTATUS:%{http_code}' -X POST "$API/admin/tenants/$NEW_TENANT/orgs" \
  -H 'content-type: application/json' \
  "${PLATFORM_HEADERS[@]}" \
  -d "{\"id\":\"$EXTRA_ORG\",\"name\":\"$EXTRA_ORG\"}")"
ORG_STATUS="${ORG_RAW##*HTTPSTATUS:}"
if [[ "$ORG_STATUS" != "200" ]]; then
  echo "Response: ${ORG_RAW%HTTPSTATUS:*}" >&2
  fail "Create org failed (status=$ORG_STATUS)"
fi
ok "Extra org created"

echo ""
echo "==> Login as new tenant admin"
NEW_TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$NEW_TENANT\",\"username\":\"$NEW_ADMIN\",\"password\":\"$NEW_PASSWORD\",\"org_id\":\"$NEW_ORG\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$NEW_TOKEN" ]]; then
  fail "New tenant admin login failed"
fi
ok "New tenant admin login"

echo ""
echo "==> Get tenant info as new admin"
INFO_RAW="$($CURL -w 'HTTPSTATUS:%{http_code}' "$API/admin/tenant" \
  -H "Authorization: Bearer $NEW_TOKEN" -H "x-tenant-id: $NEW_TENANT")"
INFO_STATUS="${INFO_RAW##*HTTPSTATUS:}"
if [[ "$INFO_STATUS" != "200" ]]; then
  echo "Response: ${INFO_RAW%HTTPSTATUS:*}" >&2
  fail "Tenant info failed (status=$INFO_STATUS)"
fi
ok "Tenant info accessible"

echo ""
echo "=============================================="
echo "Tenant Provisioning Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
