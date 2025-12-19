#!/usr/bin/env bash
# =============================================================================
# S1 Permission Verification Script
# =============================================================================
# Validates RBAC/ACE permission system:
# 1. Admin user can perform all operations
# 2. Viewer user (read-only) can only get/search, not add/update
# 3. 403 is returned for unauthorized operations
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
FAILED=0

fail() {
  echo "FAIL: $1" >&2
  FAILED=1
}

# =============================================================================
# Step 1: Seed identity - admin and viewer users
# =============================================================================
echo "==> Seed identity (admin + viewer)"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username viewer --password viewer --user-id 2 --roles viewer --no-superuser >/dev/null
echo "Created users: admin (superuser), viewer (no write)"

echo "==> Seed meta schema"
"$CLI" seed-meta >/dev/null

# =============================================================================
# Step 2: Login as admin and configure permissions
# =============================================================================
echo "==> Login as admin"
ADMIN_TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"
echo "Admin login: OK"

# =============================================================================
# Step 3: Create PermissionSet for read-only access
# =============================================================================
echo "==> Configure PermissionSets"

# Create ReadOnly permission
READONLY_PERM_ID="ReadOnly-$TS"
HTTP_CODE="$(curl -s -o /tmp/perm_create.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/meta/permissions" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"id\":\"$READONLY_PERM_ID\",\"name\":\"Read Only Permission\"}"
)"
if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "201" ]]; then
  echo "Created PermissionSet: $READONLY_PERM_ID"
else
  fail "Failed to create PermissionSet: HTTP $HTTP_CODE"
fi

# Add ACE: 'viewer' role can only get/discover
curl -s -X POST "$BASE/api/v1/meta/permissions/$READONLY_PERM_ID/accesses" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"identity_id":"viewer","can_create":false,"can_get":true,"can_update":false,"can_delete":false,"can_discover":true}' \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("can_create")==False and d.get("can_get")==True;print("ACE viewer (read-only): OK")'

# Add ACE: 'admin' role has full access
curl -s -X POST "$BASE/api/v1/meta/permissions/$READONLY_PERM_ID/accesses" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"identity_id":"admin","can_create":true,"can_get":true,"can_update":true,"can_delete":true,"can_discover":true}' \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("can_create")==True;print("ACE admin (full): OK")'

# =============================================================================
# Step 4: Assign ReadOnly permission to Part and Part BOM
# =============================================================================
echo "==> Assign PermissionSet to ItemTypes"

curl -s -X PATCH "$BASE/api/v1/meta/item-types/Part/permission" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"permission_id\":\"$READONLY_PERM_ID\"}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok")==True;print("Assigned permission to Part: OK")'

curl -s -X PATCH "$BASE/api/v1/meta/item-types/Part%20BOM/permission" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"permission_id\":\"$READONLY_PERM_ID\"}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok")==True;print("Assigned permission to Part BOM: OK")'

# =============================================================================
# Step 5: Admin creates a Part (should succeed)
# =============================================================================
echo "==> Admin creates Part (should succeed)"
PN="P-PERM-$TS"
PART_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN\",\"name\":\"Permission Test Part\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Admin AML add Part: OK (part_id=$PART_ID)"

# Create child part for BOM test
PN_CHILD="P-PERM-CHILD-$TS"
CHILD_PART_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_CHILD\",\"name\":\"Child Part\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Admin created child Part: OK (child_id=$CHILD_PART_ID)"

# =============================================================================
# Step 6: Login as viewer
# =============================================================================
echo "==> Login as viewer"
VIEWER_TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"viewer\",\"password\":\"viewer\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"
echo "Viewer login: OK"

# =============================================================================
# Step 7: Viewer READ operations (should succeed - 200)
# =============================================================================
echo "==> Viewer READ operations (should succeed)"

# AML get
curl -s "$BASE/api/v1/aml/apply" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"type\":\"Part\",\"action\":\"get\",\"properties\":{\"item_number\":\"$PN\"}}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("count",0)>=1;print("Viewer AML get Part: OK (200)")'

# Search
HTTP_CODE="$(curl -s -o /tmp/search_result.json -w '%{http_code}' \
  "$BASE/api/v1/search/?q=$PN&item_type=Part" \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
if [[ "$HTTP_CODE" == "200" ]]; then
  echo "Viewer search: OK (200)"
else
  fail "Viewer search should be 200, got $HTTP_CODE"
fi

# BOM tree
HTTP_CODE="$(curl -s -o /tmp/bom_result.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_ID/effective" \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
if [[ "$HTTP_CODE" == "200" ]]; then
  echo "Viewer BOM effective: OK (200)"
else
  fail "Viewer BOM effective should be 200, got $HTTP_CODE"
fi

# =============================================================================
# Step 8: Viewer WRITE operations (should fail - 403)
# =============================================================================
echo "==> Viewer WRITE operations (should fail with 403)"

# AML add Part - should be 403
PN_VIEWER="P-VIEWER-$TS"
HTTP_CODE="$(curl -s -o /tmp/viewer_add.json -w '%{http_code}' \
  "$BASE/api/v1/aml/apply" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_VIEWER\",\"name\":\"Viewer Part\"}}"
)"
if [[ "$HTTP_CODE" == "403" ]]; then
  echo "Viewer AML add Part: BLOCKED (403) - EXPECTED"
else
  fail "Viewer AML add Part should be 403, got $HTTP_CODE"
fi

# AML add Part BOM (relationship) - should be 403
HTTP_CODE="$(curl -s -o /tmp/viewer_bom_add.json -w '%{http_code}' \
  "$BASE/api/v1/aml/apply" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$PART_ID\",\"relationships\":[{\"type\":\"Part BOM\",\"action\":\"add\",\"properties\":{\"related_id\":\"$CHILD_PART_ID\",\"quantity\":\"2\"}}]}"
)"
if [[ "$HTTP_CODE" == "403" ]]; then
  echo "Viewer BOM add child: BLOCKED (403) - EXPECTED"
else
  fail "Viewer BOM add child should be 403, got $HTTP_CODE"
fi

# AML update - should be 403
HTTP_CODE="$(curl -s -o /tmp/viewer_update.json -w '%{http_code}' \
  "$BASE/api/v1/aml/apply" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$PART_ID\",\"properties\":{\"name\":\"Updated by Viewer\"}}"
)"
if [[ "$HTTP_CODE" == "403" ]]; then
  echo "Viewer AML update Part: BLOCKED (403) - EXPECTED"
else
  fail "Viewer AML update Part should be 403, got $HTTP_CODE"
fi

# =============================================================================
# Step 9: Admin can still write (verify admin access)
# =============================================================================
echo "==> Admin WRITE operations (should succeed)"

# Admin BOM add child
curl -s "$BASE/api/v1/aml/apply" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$PART_ID\",\"relationships\":[{\"type\":\"Part BOM\",\"action\":\"add\",\"properties\":{\"related_id\":\"$CHILD_PART_ID\",\"quantity\":\"2\"}}]}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("status")=="updated";print("Admin BOM add child: OK")'

# Admin update Part
curl -s "$BASE/api/v1/aml/apply" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$PART_ID\",\"properties\":{\"name\":\"Updated by Admin\"}}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("status")=="updated";print("Admin AML update Part: OK")'

# =============================================================================
# Step 10: Verify BOM tree shows the child (viewer can still read)
# =============================================================================
echo "==> Viewer can read updated BOM tree"
curl -s "$BASE/api/v1/bom/$PART_ID/effective" \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert len(d.get("children",[]))>=1;print("Viewer BOM tree with children: OK (200)")'

# =============================================================================
# Summary
# =============================================================================
echo
if [[ "$FAILED" -eq 0 ]]; then
  echo "ALL CHECKS PASSED"
else
  echo "SOME CHECKS FAILED"
  exit 1
fi
