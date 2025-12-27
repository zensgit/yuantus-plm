#!/usr/bin/env bash
# =============================================================================
# Part Lifecycle & BOM Lock Verification Script
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

TS="$(date +%s)"
TMP_FILE="/tmp/yuantus_part_lifecycle_${TS}.txt"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

echo "=============================================="
echo "Part Lifecycle Verification"
echo "BASE_URL: $BASE"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null
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

echo ""
echo "==> Create Parts"
PARENT_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"PLC-${TS}-A\",\"name\":\"Lifecycle Parent\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"PLC-${TS}-B\",\"name\":\"Lifecycle Child\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD2_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"PLC-${TS}-C\",\"name\":\"Lifecycle Child 2\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
if [[ -z "$PARENT_ID" || -z "$CHILD_ID" || -z "$CHILD2_ID" ]]; then
  fail "Part creation failed"
fi
echo "OK: Created parent=$PARENT_ID child=$CHILD_ID child2=$CHILD2_ID"

echo ""
echo "==> Add BOM child in Draft"
REL_ID="$(
  curl -s -X POST "$BASE/api/v1/bom/${PARENT_ID}/children" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":1}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["relationship_id"])'
)"
if [[ -z "$REL_ID" ]]; then
  fail "BOM add failed in Draft"
fi
echo "OK: BOM relationship $REL_ID"

echo ""
echo "==> Promote to Review"
PROMOTE_REVIEW="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"promote\",\"id\":\"$PARENT_ID\",\"properties\":{\"target_state\":\"Review\"}}"
)"
PROMOTE_REVIEW_STATE="$(echo "$PROMOTE_REVIEW" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))')"
if [[ "$PROMOTE_REVIEW_STATE" != "Review" ]]; then
  fail "Expected Review state, got '$PROMOTE_REVIEW_STATE'"
fi
echo "OK: State Review"

echo ""
echo "==> Promote to Released"
PROMOTE_RELEASE="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"promote\",\"id\":\"$PARENT_ID\",\"properties\":{\"target_state\":\"Released\"}}"
)"
PROMOTE_RELEASE_STATE="$(echo "$PROMOTE_RELEASE" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))')"
if [[ "$PROMOTE_RELEASE_STATE" != "Released" ]]; then
  fail "Expected Released state, got '$PROMOTE_RELEASE_STATE'"
fi
echo "OK: State Released"

echo ""
echo "==> Update after Release should be blocked"
UPDATE_CODE="$(
  curl -s -o /tmp/yuantus_part_update.json -w '%{http_code}' \
    "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$PARENT_ID\",\"properties\":{\"description\":\"Released update\"}}"
)"
if [[ "$UPDATE_CODE" != "409" ]]; then
  cat /tmp/yuantus_part_update.json >&2 || true
  fail "Expected 409 on update after release, got $UPDATE_CODE"
fi
echo "OK: Update blocked (409)"

echo ""
echo "==> BOM add after Release should be blocked"
BOM_ADD_CODE="$(
  curl -s -o /tmp/yuantus_part_bom_add.json -w '%{http_code}' \
    -X POST "$BASE/api/v1/bom/${PARENT_ID}/children" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$CHILD2_ID\",\"quantity\":1}"
)"
if [[ "$BOM_ADD_CODE" != "409" ]]; then
  cat /tmp/yuantus_part_bom_add.json >&2 || true
  fail "Expected 409 on BOM add after release, got $BOM_ADD_CODE"
fi
echo "OK: BOM add blocked (409)"

echo ""
echo "==> BOM remove after Release should be blocked"
BOM_DEL_CODE="$(
  curl -s -o /tmp/yuantus_part_bom_del.json -w '%{http_code}' \
    -X DELETE "$BASE/api/v1/bom/${PARENT_ID}/children/${CHILD_ID}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
if [[ "$BOM_DEL_CODE" != "409" ]]; then
  cat /tmp/yuantus_part_bom_del.json >&2 || true
  fail "Expected 409 on BOM delete after release, got $BOM_DEL_CODE"
fi
echo "OK: BOM delete blocked (409)"

echo ""
echo "==> Attach file after Release should be blocked"
echo "Part lifecycle test file $TS" > "$TMP_FILE"
UPLOAD_JSON="$(
  curl -s -X POST "$BASE/api/v1/file/upload?generate_preview=false" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -F "file=@${TMP_FILE}"
)"
FILE_ID="$(echo "$UPLOAD_JSON" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
if [[ -z "$FILE_ID" ]]; then
  fail "Upload failed"
fi
ATTACH_CODE="$(
  curl -s -o /tmp/yuantus_part_attach.json -w '%{http_code}' \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -X POST "$BASE/api/v1/file/attach" \
    -d "{\"item_id\":\"$PARENT_ID\",\"file_id\":\"$FILE_ID\",\"file_role\":\"attachment\"}"
)"
if [[ "$ATTACH_CODE" != "409" ]]; then
  cat /tmp/yuantus_part_attach.json >&2 || true
  fail "Expected 409 on attach after release, got $ATTACH_CODE"
fi
echo "OK: Attach blocked (409)"

echo ""
echo "==> Cleanup"
rm -f "$TMP_FILE"

echo ""
echo "=============================================="
echo "Part Lifecycle Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
