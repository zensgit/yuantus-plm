#!/usr/bin/env bash
# =============================================================================
# Lifecycle Suspended State Verification Script
# =============================================================================
set -euo pipefail

BASE="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

echo "=============================================="
echo "Lifecycle Suspended Verification"
echo "BASE_URL: $BASE"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || "$CLI" seed-meta >/dev/null
echo "OK: Seeded identity/meta"

echo ""
echo "==> Login as admin"
TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"
if [[ -z "$TOKEN" ]]; then
  fail "Admin login failed"
fi
echo "OK: Admin login"

TS="$(date +%s)"
echo ""
echo "==> Create Part"
PART_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUS-${TS}\",\"name\":\"Suspended Test\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
if [[ -z "$PART_ID" ]]; then
  fail "Part creation failed"
fi
echo "OK: Created Part $PART_ID"

echo ""
echo "==> Promote to Review"
STATE="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"promote\",\"id\":\"$PART_ID\",\"properties\":{\"target_state\":\"Review\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))'
)"
if [[ "$STATE" != "Review" ]]; then
  fail "Expected Review, got $STATE"
fi
echo "OK: State Review"

echo ""
echo "==> Promote to Released"
STATE="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"promote\",\"id\":\"$PART_ID\",\"properties\":{\"target_state\":\"Released\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))'
)"
if [[ "$STATE" != "Released" ]]; then
  fail "Expected Released, got $STATE"
fi
echo "OK: State Released"

echo ""
echo "==> Promote to Suspended"
STATE="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"promote\",\"id\":\"$PART_ID\",\"properties\":{\"target_state\":\"Suspended\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))'
)"
if [[ "$STATE" != "Suspended" ]]; then
  fail "Expected Suspended, got $STATE"
fi
echo "OK: State Suspended"

echo ""
echo "==> Update in Suspended should be blocked"
UPDATE_CODE="$(
  curl -s -o /tmp/yuantus_part_suspended_update.json -w '%{http_code}' \
    "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$PART_ID\",\"properties\":{\"description\":\"Suspended update\"}}"
)"
if [[ "$UPDATE_CODE" != "409" ]]; then
  cat /tmp/yuantus_part_suspended_update.json >&2 || true
  fail "Expected 409 on update in Suspended, got $UPDATE_CODE"
fi
echo "OK: Update blocked (409)"

echo ""
echo "==> Resume to Released"
STATE="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"promote\",\"id\":\"$PART_ID\",\"properties\":{\"target_state\":\"Released\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))'
)"
if [[ "$STATE" != "Released" ]]; then
  fail "Expected Released after resume, got $STATE"
fi
echo "OK: State Released"

echo "=============================================="
echo "Lifecycle Suspended Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
