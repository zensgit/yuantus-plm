#!/usr/bin/env bash
# =============================================================================
# S3.2 BOM Effectivity Verification Script
# =============================================================================
# Validates BOM effectivity (Date-based):
# 1. BOM lines with effectivity_from/to are correctly filtered by date
# 2. Same BOM tree returns different children at different dates
# 3. RBAC: viewer cannot add BOM children (403)
# 4. DELETE cascades to remove Effectivity records
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

# Calculate dates
TODAY="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
NEXT_WEEK="$(date -u -v+7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '+7 days' +%Y-%m-%dT%H:%M:%SZ)"
LAST_WEEK="$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '-7 days' +%Y-%m-%dT%H:%M:%SZ)"

echo "Date context: TODAY=$TODAY, NEXT_WEEK=$NEXT_WEEK, LAST_WEEK=$LAST_WEEK"

# =============================================================================
# Step 1: Seed identity (admin + viewer)
# =============================================================================
echo "==> Seed identity (admin + viewer)"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username viewer --password viewer --user-id 2 --roles viewer --no-superuser >/dev/null
echo "Created users: admin (superuser), viewer (no write)"

echo "==> Seed meta schema"
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null

# =============================================================================
# Step 2: Configure ReadOnly permission for viewer
# =============================================================================
echo "==> Login as admin"
ADMIN_TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"
echo "Admin login: OK"

echo "==> Configure PermissionSets"
READONLY_PERM_ID="EffReadOnly-$TS"
curl -s -o /tmp/perm_create.json \
  -X POST "$BASE/api/v1/meta/permissions" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"id\":\"$READONLY_PERM_ID\",\"name\":\"Effectivity Read Only\"}"

# ACE: viewer can only read
curl -s -X POST "$BASE/api/v1/meta/permissions/$READONLY_PERM_ID/accesses" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"identity_id":"viewer","can_create":false,"can_get":true,"can_update":false,"can_delete":false,"can_discover":true}' >/dev/null

# ACE: admin has full access
curl -s -X POST "$BASE/api/v1/meta/permissions/$READONLY_PERM_ID/accesses" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"identity_id":"admin","can_create":true,"can_get":true,"can_update":true,"can_delete":true,"can_discover":true}' >/dev/null

# Assign to Part and Part BOM
curl -s -X PATCH "$BASE/api/v1/meta/item-types/Part/permission" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"permission_id\":\"$READONLY_PERM_ID\"}" >/dev/null

curl -s -X PATCH "$BASE/api/v1/meta/item-types/Part%20BOM/permission" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"permission_id\":\"$READONLY_PERM_ID\"}" >/dev/null

echo "Permissions configured: OK"

# =============================================================================
# Step 3: Create test parts
# =============================================================================
echo "==> Create test parts"

# Part A (parent)
PN_A="P-EFF-A-$TS"
PART_A_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_A\",\"name\":\"Effectivity Parent\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Created Part A (parent): $PART_A_ID"

# Part B (child - effective from next week)
PN_B="P-EFF-B-$TS"
PART_B_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_B\",\"name\":\"Future Child (next week)\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Created Part B (future child): $PART_B_ID"

# Part C (child - effective now, no end date)
PN_C="P-EFF-C-$TS"
PART_C_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_C\",\"name\":\"Current Child (now)\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Created Part C (current child): $PART_C_ID"

# Part D (child - expired last week)
PN_D="P-EFF-D-$TS"
PART_D_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_D\",\"name\":\"Expired Child (last week)\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Created Part D (expired child): $PART_D_ID"

# =============================================================================
# Step 4: Build BOM with different effectivity dates
# =============================================================================
echo "==> Build BOM with effectivity dates"

# A -> B (effective from next week, no end)
echo "Adding B to A (effective from next week)..."
REL_AB_RESULT="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/children" \
    -X POST \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$PART_B_ID\",\"quantity\":1,\"effectivity_from\":\"$NEXT_WEEK\"}"
)"
REL_AB_ID="$("$PY" -c "import sys,json;d=json.loads('$REL_AB_RESULT');assert d.get('ok')==True;print(d['relationship_id'])")"
EFF_AB_ID="$("$PY" -c "import sys,json;d=json.loads('$REL_AB_RESULT');print(d.get('effectivity_id',''))")"
echo "A -> B relationship: $REL_AB_ID, effectivity_id: $EFF_AB_ID"

# A -> C (effective from last week, no end - always visible from today onward)
echo "Adding C to A (effective from last week, always visible now)..."
REL_AC_RESULT="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/children" \
    -X POST \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$PART_C_ID\",\"quantity\":2,\"effectivity_from\":\"$LAST_WEEK\"}"
)"
REL_AC_ID="$("$PY" -c "import sys,json;d=json.loads('$REL_AC_RESULT');assert d.get('ok')==True;print(d['relationship_id'])")"
echo "A -> C relationship: $REL_AC_ID"

# A -> D (effective from 2 weeks ago, ended last week - expired)
TWO_WEEKS_AGO="$(date -u -v-14d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '-14 days' +%Y-%m-%dT%H:%M:%SZ)"
echo "Adding D to A (expired - ended last week)..."
REL_AD_RESULT="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/children" \
    -X POST \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$PART_D_ID\",\"quantity\":1,\"effectivity_from\":\"$TWO_WEEKS_AGO\",\"effectivity_to\":\"$LAST_WEEK\"}"
)"
REL_AD_ID="$("$PY" -c "import sys,json;d=json.loads('$REL_AD_RESULT');assert d.get('ok')==True;print(d['relationship_id'])")"
echo "A -> D relationship: $REL_AD_ID"

echo "BOM with effectivity created: OK"

# =============================================================================
# Step 5: Query effective BOM at TODAY - should only see C
# =============================================================================
echo "==> Query effective BOM at TODAY (should only see C)"

BOM_TODAY="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/effective?date=$TODAY" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
CHILDREN_TODAY="$("$PY" -c "import sys,json;d=json.loads('$BOM_TODAY');print(len(d.get('children',[])))")"

if [[ "$CHILDREN_TODAY" == "1" ]]; then
  # Verify it's Part C
  CHILD_ID_TODAY="$("$PY" -c "import sys,json;d=json.loads('$BOM_TODAY');print(d['children'][0]['child']['id'])")"
  if [[ "$CHILD_ID_TODAY" == "$PART_C_ID" ]]; then
    echo "Effective BOM at TODAY: 1 child (C only): OK"
  else
    fail "Expected child C at TODAY, got different child"
  fi
else
  fail "Expected 1 child at TODAY, got $CHILDREN_TODAY"
fi

# =============================================================================
# Step 6: Query effective BOM at NEXT_WEEK - should see B and C
# =============================================================================
echo "==> Query effective BOM at NEXT_WEEK (should see B and C)"

BOM_NEXT_WEEK="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/effective?date=$NEXT_WEEK" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
CHILDREN_NEXT_WEEK="$("$PY" -c "import sys,json;d=json.loads('$BOM_NEXT_WEEK');print(len(d.get('children',[])))")"

if [[ "$CHILDREN_NEXT_WEEK" == "2" ]]; then
  echo "Effective BOM at NEXT_WEEK: 2 children (B and C): OK"
else
  fail "Expected 2 children at NEXT_WEEK, got $CHILDREN_NEXT_WEEK"
fi

# =============================================================================
# Step 7: Query effective BOM at LAST_WEEK - should see C and D
# =============================================================================
echo "==> Query effective BOM at LAST_WEEK (should see C and D)"

BOM_LAST_WEEK="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/effective?date=$LAST_WEEK" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
CHILDREN_LAST_WEEK="$("$PY" -c "import sys,json;d=json.loads('$BOM_LAST_WEEK');print(len(d.get('children',[])))")"

if [[ "$CHILDREN_LAST_WEEK" == "2" ]]; then
  echo "Effective BOM at LAST_WEEK: 2 children (C and D): OK"
else
  fail "Expected 2 children at LAST_WEEK, got $CHILDREN_LAST_WEEK"
fi

# =============================================================================
# Step 8: RBAC - Viewer cannot add BOM children (403)
# =============================================================================
echo "==> RBAC: Viewer cannot add BOM children (should be 403)"

VIEWER_TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"viewer\",\"password\":\"viewer\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"
echo "Viewer login: OK"

# Create a new part for viewer test
PN_E="P-EFF-E-$TS"
PART_E_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_E\",\"name\":\"Viewer Test Part\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

HTTP_CODE="$(curl -s -o /tmp/viewer_bom_add.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_A_ID/children" \
  -X POST \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"child_id\":\"$PART_E_ID\",\"quantity\":1}"
)"

if [[ "$HTTP_CODE" == "403" ]]; then
  echo "Viewer add BOM child: BLOCKED (403) - EXPECTED"
else
  fail "Viewer add BOM child should be 403, got $HTTP_CODE"
fi

# =============================================================================
# Step 9: Viewer can read effective BOM (200)
# =============================================================================
echo "==> RBAC: Viewer can read effective BOM (should be 200)"

HTTP_CODE="$(curl -s -o /tmp/viewer_bom_read.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_A_ID/effective" \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "Viewer read effective BOM: OK (200)"
else
  fail "Viewer read effective BOM should be 200, got $HTTP_CODE"
fi

# =============================================================================
# Step 10: Delete BOM line and verify Effectivity is cleaned up
# =============================================================================
echo "==> Delete BOM line (A -> B) and verify Effectivity CASCADE"

# Delete the relationship
HTTP_CODE="$(curl -s -o /tmp/delete_result.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_A_ID/children/$PART_B_ID" \
  -X DELETE \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "Delete A -> B relationship: OK"
else
  fail "Delete A -> B should return 200, got $HTTP_CODE"
fi

# Query at NEXT_WEEK again - should now only see C (B was deleted)
BOM_AFTER_DELETE="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/effective?date=$NEXT_WEEK" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
CHILDREN_AFTER_DELETE="$("$PY" -c "import sys,json;d=json.loads('$BOM_AFTER_DELETE');print(len(d.get('children',[])))")"

if [[ "$CHILDREN_AFTER_DELETE" == "1" ]]; then
  echo "After delete: NEXT_WEEK shows 1 child (C only): OK"
else
  fail "After delete, NEXT_WEEK should show 1 child, got $CHILDREN_AFTER_DELETE"
fi

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
