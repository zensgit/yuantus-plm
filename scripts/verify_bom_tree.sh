#!/usr/bin/env bash
# =============================================================================
# S3.1 Multi-level BOM + Cycle Detection Verification Script
# =============================================================================
# Validates BOM tree operations:
# 1. POST /api/v1/bom/{parent_id}/children - add child
# 2. DELETE /api/v1/bom/{parent_id}/children/{child_id} - remove child
# 3. GET /api/v1/bom/{parent_id}/tree?depth=... - tree query
# 4. Cycle detection returns 409 with cycle path
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
# Step 1: Seed identity and meta
# =============================================================================
echo "==> Seed identity"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
echo "Created admin user"

echo "==> Seed meta schema"
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null

# =============================================================================
# Step 2: Login as admin
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
# Step 3: Create test parts (A, B, C, D) for multi-level BOM
# =============================================================================
echo "==> Create test parts for BOM tree"

# Part A (top-level)
PN_A="P-BOM-A-$TS"
PART_A_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_A\",\"name\":\"Part A (Top)\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Created Part A: $PART_A_ID"

# Part B (level 2)
PN_B="P-BOM-B-$TS"
PART_B_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_B\",\"name\":\"Part B (Level 2)\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Created Part B: $PART_B_ID"

# Part C (level 3)
PN_C="P-BOM-C-$TS"
PART_C_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_C\",\"name\":\"Part C (Level 3)\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Created Part C: $PART_C_ID"

# Part D (another level 3 sibling)
PN_D="P-BOM-D-$TS"
PART_D_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN_D\",\"name\":\"Part D (Level 3 sibling)\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "Created Part D: $PART_D_ID"

# =============================================================================
# Step 4: Build BOM structure using POST /bom/{parent_id}/children
# Structure: A -> B -> C
#                 \-> D
# =============================================================================
echo "==> Build BOM structure: A -> B -> C, B -> D"

# A -> B (qty=2, uom=EA, find_num=10)
echo "Adding B as child of A..."
REL_AB_ID="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/children" \
    -X POST \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$PART_B_ID\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"10\"}" \
    | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok")==True;print(d["relationship_id"])'
)"
echo "A -> B relationship created: $REL_AB_ID"

# B -> C (qty=3, uom=KG, find_num=20)
echo "Adding C as child of B..."
REL_BC_ID="$(
  curl -s "$BASE/api/v1/bom/$PART_B_ID/children" \
    -X POST \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$PART_C_ID\",\"quantity\":3,\"uom\":\"KG\",\"find_num\":\"20\"}" \
    | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok")==True;print(d["relationship_id"])'
)"
echo "B -> C relationship created: $REL_BC_ID"

# B -> D (qty=1, uom=EA, find_num=30)
echo "Adding D as child of B..."
REL_BD_ID="$(
  curl -s "$BASE/api/v1/bom/$PART_B_ID/children" \
    -X POST \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$PART_D_ID\",\"quantity\":1,\"uom\":\"EA\",\"find_num\":\"30\"}" \
    | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok")==True;print(d["relationship_id"])'
)"
echo "B -> D relationship created: $REL_BD_ID"

echo "BOM structure created: OK"

# =============================================================================
# Step 5: Test GET /bom/{parent_id}/tree with depth parameter
# =============================================================================
echo "==> Test BOM tree query with depth"

# Full tree (depth=10)
TREE_FULL="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/tree?depth=10" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
CHILD_COUNT_L1="$("$PY" -c "import sys,json;d=json.loads('$TREE_FULL');print(len(d.get('children',[])))")"
if [[ "$CHILD_COUNT_L1" == "1" ]]; then
  echo "Full tree (depth=10): Level 1 has 1 child (B): OK"
else
  fail "Full tree should have 1 child at level 1, got $CHILD_COUNT_L1"
fi

# Check level 2 has 2 children (C and D)
CHILD_COUNT_L2="$("$PY" -c "import sys,json;d=json.loads('$TREE_FULL');print(len(d.get('children',[])[0].get('child',{}).get('children',[])))")"
if [[ "$CHILD_COUNT_L2" == "2" ]]; then
  echo "Full tree (depth=10): Level 2 has 2 children (C, D): OK"
else
  fail "Full tree should have 2 children at level 2, got $CHILD_COUNT_L2"
fi

# Limited tree (depth=1) - should only show B, not C/D
TREE_L1="$(
  curl -s "$BASE/api/v1/bom/$PART_A_ID/tree?depth=1" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
CHILD_COUNT_L1_LIMITED="$("$PY" -c "import sys,json;d=json.loads('$TREE_L1');print(len(d.get('children',[])))")"
GRANDCHILD_COUNT="$("$PY" -c "import sys,json;d=json.loads('$TREE_L1');c=d.get('children',[]);print(len(c[0].get('child',{}).get('children',[])) if c else 0)")"
if [[ "$CHILD_COUNT_L1_LIMITED" == "1" ]] && [[ "$GRANDCHILD_COUNT" == "0" ]]; then
  echo "Limited tree (depth=1): Only shows B with no grandchildren: OK"
else
  fail "Limited tree (depth=1) should show 1 child with 0 grandchildren, got $CHILD_COUNT_L1_LIMITED children, $GRANDCHILD_COUNT grandchildren"
fi

# =============================================================================
# Step 6: Test cycle detection - C -> A should return 409
# =============================================================================
echo "==> Test cycle detection (C -> A should be 409)"

HTTP_CODE="$(curl -s -o /tmp/cycle_response.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_C_ID/children" \
  -X POST \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"child_id\":\"$PART_A_ID\",\"quantity\":1}"
)"

if [[ "$HTTP_CODE" == "409" ]]; then
  echo "Cycle detection: C -> A returned 409: OK"

  # Verify cycle path is returned
  CYCLE_ERROR="$("$PY" -c 'import sys,json;d=json.load(open("/tmp/cycle_response.json"));print(d.get("error",""))')"
  CYCLE_PATH="$("$PY" -c 'import sys,json;d=json.load(open("/tmp/cycle_response.json"));print(d.get("cycle_path",[]))')"

  if [[ "$CYCLE_ERROR" == "CYCLE_DETECTED" ]]; then
    echo "Cycle error type: CYCLE_DETECTED: OK"
  else
    fail "Expected error type 'CYCLE_DETECTED', got '$CYCLE_ERROR'"
  fi

  if [[ -n "$CYCLE_PATH" ]] && [[ "$CYCLE_PATH" != "[]" ]]; then
    echo "Cycle path returned: $CYCLE_PATH: OK"
  else
    fail "Expected non-empty cycle path, got '$CYCLE_PATH'"
  fi
else
  fail "Cycle detection should return 409, got $HTTP_CODE"
  cat /tmp/cycle_response.json
fi

# =============================================================================
# Step 7: Test self-reference cycle (A -> A)
# =============================================================================
echo "==> Test self-reference cycle (A -> A should be 409)"

HTTP_CODE="$(curl -s -o /tmp/self_cycle.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_A_ID/children" \
  -X POST \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"child_id\":\"$PART_A_ID\",\"quantity\":1}"
)"

if [[ "$HTTP_CODE" == "409" ]]; then
  echo "Self-reference cycle: A -> A returned 409: OK"
else
  fail "Self-reference cycle should return 409, got $HTTP_CODE"
fi

# =============================================================================
# Step 8: Test duplicate add prevention
# =============================================================================
echo "==> Test duplicate add (A -> B again should fail)"

HTTP_CODE="$(curl -s -o /tmp/duplicate.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_A_ID/children" \
  -X POST \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"child_id\":\"$PART_B_ID\",\"quantity\":1}"
)"

if [[ "$HTTP_CODE" == "400" ]]; then
  echo "Duplicate add: A -> B again returned 400: OK"
else
  fail "Duplicate add should return 400, got $HTTP_CODE"
fi

# =============================================================================
# Step 9: Test DELETE /bom/{parent_id}/children/{child_id}
# =============================================================================
echo "==> Test remove child (B -> D)"

# Remove D from B
HTTP_CODE="$(curl -s -o /tmp/remove_result.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_B_ID/children/$PART_D_ID" \
  -X DELETE \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "Remove child: B -> D deleted: OK"

  # Verify D is no longer in tree
  TREE_AFTER_DELETE="$(
    curl -s "$BASE/api/v1/bom/$PART_A_ID/tree?depth=10" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
  )"
  CHILD_COUNT_L2_AFTER="$("$PY" -c "import sys,json;d=json.loads('$TREE_AFTER_DELETE');print(len(d.get('children',[])[0].get('child',{}).get('children',[])))")"

  if [[ "$CHILD_COUNT_L2_AFTER" == "1" ]]; then
    echo "After delete: Level 2 has 1 child (C only): OK"
  else
    fail "After delete, level 2 should have 1 child, got $CHILD_COUNT_L2_AFTER"
  fi
else
  fail "Remove child should return 200, got $HTTP_CODE"
fi

# =============================================================================
# Step 10: Test remove non-existent relationship
# =============================================================================
echo "==> Test remove non-existent relationship"

HTTP_CODE="$(curl -s -o /tmp/remove_404.json -w '%{http_code}' \
  "$BASE/api/v1/bom/$PART_A_ID/children/$PART_D_ID" \
  -X DELETE \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"

if [[ "$HTTP_CODE" == "404" ]]; then
  echo "Remove non-existent: A -> D (never existed) returned 404: OK"
else
  fail "Remove non-existent should return 404, got $HTTP_CODE"
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
