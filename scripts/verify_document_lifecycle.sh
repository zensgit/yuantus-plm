#!/usr/bin/env bash
# =============================================================================
# Document Lifecycle & Controlled Release Verification Script
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
TMP_FILE="/tmp/yuantus_doc_lifecycle_${TS}.txt"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

echo "=============================================="
echo "Document Lifecycle Verification"
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
echo "==> Create Document"
DOC_NO="DOC-${TS}"
DOC_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Document\",\"action\":\"add\",\"properties\":{\"doc_number\":\"$DOC_NO\",\"name\":\"Lifecycle Doc\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
if [[ -z "$DOC_ID" ]]; then
  fail "Document creation failed"
fi
echo "OK: Created Document: $DOC_ID"

echo ""
echo "==> Initialize version"
VER_INIT="$(
  curl -s -X POST "$BASE/api/v1/versions/items/$DOC_ID/init" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
VER_LABEL="$(echo "$VER_INIT" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("version_label",""))')"
if [[ "$VER_LABEL" != "1.A" ]]; then
  fail "Expected version 1.A, got '$VER_LABEL'"
fi
echo "OK: Initial version $VER_LABEL"

echo ""
echo "==> Verify initial state is Draft"
DOC_STATE="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Document\",\"action\":\"get\",\"id\":\"$DOC_ID\"}" \
    | "$PY" -c 'import sys,json;data=json.load(sys.stdin);items=data.get("items",[]);print(items[0].get("state",""))'
)"
if [[ "$DOC_STATE" != "Draft" ]]; then
  fail "Expected state Draft, got '$DOC_STATE'"
fi
echo "OK: State Draft"

echo ""
echo "==> Update Document in Draft"
UPDATE_RESP="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Document\",\"action\":\"update\",\"id\":\"$DOC_ID\",\"properties\":{\"description\":\"Draft update\"}}"
)"
UPDATE_STATUS="$(echo "$UPDATE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status",""))')"
if [[ "$UPDATE_STATUS" != "updated" ]]; then
  fail "Draft update failed"
fi
echo "OK: Draft update"

echo ""
echo "==> Promote to Review"
PROMOTE_REVIEW="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Document\",\"action\":\"promote\",\"id\":\"$DOC_ID\",\"properties\":{\"target_state\":\"Review\"}}"
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
    -d "{\"type\":\"Document\",\"action\":\"promote\",\"id\":\"$DOC_ID\",\"properties\":{\"target_state\":\"Released\"}}"
)"
PROMOTE_RELEASE_STATE="$(echo "$PROMOTE_RELEASE" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))')"
if [[ "$PROMOTE_RELEASE_STATE" != "Released" ]]; then
  fail "Expected Released state, got '$PROMOTE_RELEASE_STATE'"
fi
echo "OK: State Released"

echo ""
echo "==> Update after Release should be blocked"
UPDATE_CODE="$(
  curl -s -o /tmp/yuantus_doc_update.json -w '%{http_code}' \
    "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Document\",\"action\":\"update\",\"id\":\"$DOC_ID\",\"properties\":{\"description\":\"Released update\"}}"
)"
if [[ "$UPDATE_CODE" != "409" ]]; then
  cat /tmp/yuantus_doc_update.json >&2 || true
  fail "Expected 409 on update after release, got $UPDATE_CODE"
fi
echo "OK: Update blocked (409)"

echo ""
echo "==> Attach file after Release should be blocked"
echo "Document lifecycle test file $TS" > "$TMP_FILE"
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
  curl -s -o /tmp/yuantus_doc_attach.json -w '%{http_code}' \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -X POST "$BASE/api/v1/file/attach" \
    -d "{\"item_id\":\"$DOC_ID\",\"file_id\":\"$FILE_ID\",\"file_role\":\"attachment\"}"
)"
if [[ "$ATTACH_CODE" != "409" ]]; then
  cat /tmp/yuantus_doc_attach.json >&2 || true
  fail "Expected 409 on attach after release, got $ATTACH_CODE"
fi
echo "OK: Attach blocked (409)"

echo ""
echo "==> Cleanup"
rm -f "$TMP_FILE"

echo ""
echo "=============================================="
echo "Document Lifecycle Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
