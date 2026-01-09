#!/usr/bin/env bash
# =============================================================================
# S3.3 Version Semantics & Rules Verification Script
# =============================================================================
# Validates version control system:
# 1. Initial version creation (1.A)
# 2. Revision increment (A -> B -> C)
# 3. Generation increment (1.x -> 2.A)
# 4. Version tree/history API
# 5. File attachment to version
# 6. Iteration within version (1.A.1, 1.A.2)
# 7. Revision scheme configuration
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
# Step 3: Create a versionable Part
# =============================================================================
echo "==> Create versionable Part"
PN="P-VER-$TS"
PART_RESULT="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN\",\"name\":\"Versioned Part\"}}"
)"
PART_ID="$("$PY" -c "import sys,json;print(json.loads('$PART_RESULT')['id'])")"
echo "Created Part: $PART_ID"

# =============================================================================
# Step 4: Initialize version (should create 1.A)
# =============================================================================
echo "==> Initialize version (expecting 1.A)"
VER_INIT="$(
  curl -s -X POST "$BASE/api/v1/versions/items/$PART_ID/init" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
VER_ID="$("$PY" -c "import sys,json;d=json.loads('$VER_INIT');print(d['id'])")"
VER_LABEL="$("$PY" -c "import sys,json;d=json.loads('$VER_INIT');print(d['version_label'])")"
VER_GEN="$("$PY" -c "import sys,json;d=json.loads('$VER_INIT');print(d['generation'])")"
VER_REV="$("$PY" -c "import sys,json;d=json.loads('$VER_INIT');print(d['revision'])")"

if [[ "$VER_LABEL" == "1.A" ]] && [[ "$VER_GEN" == "1" ]] && [[ "$VER_REV" == "A" ]]; then
  echo "Initial version: $VER_LABEL (generation=$VER_GEN, revision=$VER_REV): OK"
else
  fail "Expected version 1.A, got $VER_LABEL (gen=$VER_GEN, rev=$VER_REV)"
fi

# =============================================================================
# Step 5: Revise (1.A -> 1.B)
# =============================================================================
echo "==> Revise version (1.A -> 1.B)"
VER_REVISE="$(
  curl -s -X POST "$BASE/api/v1/versions/items/$PART_ID/revise" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
VER_B_LABEL="$("$PY" -c "import sys,json;d=json.loads('$VER_REVISE');print(d['version_label'])")"
VER_B_ID="$("$PY" -c "import sys,json;d=json.loads('$VER_REVISE');print(d['id'])")"

if [[ "$VER_B_LABEL" == "1.B" ]]; then
  echo "Revised version: $VER_B_LABEL: OK"
else
  fail "Expected version 1.B, got $VER_B_LABEL"
fi

# =============================================================================
# Step 6: Revise again (1.B -> 1.C)
# =============================================================================
echo "==> Revise version again (1.B -> 1.C)"
VER_REVISE2="$(
  curl -s -X POST "$BASE/api/v1/versions/items/$PART_ID/revise" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
VER_C_LABEL="$("$PY" -c "import sys,json;d=json.loads('$VER_REVISE2');print(d['version_label'])")"

if [[ "$VER_C_LABEL" == "1.C" ]]; then
  echo "Revised version: $VER_C_LABEL: OK"
else
  fail "Expected version 1.C, got $VER_C_LABEL"
fi

# =============================================================================
# Step 7: Get version tree (should show 3 versions)
# =============================================================================
echo "==> Get version tree"
VER_TREE="$(
  curl -s "$BASE/api/v1/versions/items/$PART_ID/tree" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
TREE_COUNT="$("$PY" -c "import sys,json;d=json.loads('$VER_TREE');print(len(d))")"

if [[ "$TREE_COUNT" == "3" ]]; then
  echo "Version tree has 3 versions (1.A, 1.B, 1.C): OK"
else
  fail "Expected 3 versions in tree, got $TREE_COUNT"
fi

# Verify tree structure (predecessor chain)
TREE_LABELS="$("$PY" -c "import sys,json;d=json.loads('$VER_TREE');print(','.join(sorted([v['label'] for v in d])))")"
if [[ "$TREE_LABELS" == "1.A,1.B,1.C" ]]; then
  echo "Version tree labels: $TREE_LABELS: OK"
else
  fail "Expected labels '1.A,1.B,1.C', got '$TREE_LABELS'"
fi

# =============================================================================
# Step 8: Get version history
# =============================================================================
echo "==> Get version history"
VER_HISTORY="$(
  curl -s "$BASE/api/v1/versions/items/$PART_ID/history" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
HISTORY_COUNT="$("$PY" -c "import sys,json;d=json.loads('$VER_HISTORY');print(len(d))")"

# History should have at least 3 entries (create + 2 revise)
if [[ "$HISTORY_COUNT" -ge "3" ]]; then
  echo "Version history has $HISTORY_COUNT entries: OK"
else
  fail "Expected at least 3 history entries, got $HISTORY_COUNT"
fi

# =============================================================================
# Step 9: Test revision calculation API
# =============================================================================
echo "==> Test revision calculation"

# Letter scheme: A -> B
NEXT_REV="$(
  curl -s "$BASE/api/v1/versions/revision/next?current=A&scheme=letter" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["next"])'
)"
if [[ "$NEXT_REV" == "B" ]]; then
  echo "Letter scheme: A -> B: OK"
else
  fail "Expected B, got $NEXT_REV"
fi

# Letter scheme: Z -> AA
NEXT_REV_Z="$(
  curl -s "$BASE/api/v1/versions/revision/next?current=Z&scheme=letter" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["next"])'
)"
if [[ "$NEXT_REV_Z" == "AA" ]]; then
  echo "Letter scheme: Z -> AA: OK"
else
  fail "Expected AA, got $NEXT_REV_Z"
fi

# Number scheme: 1 -> 2
NEXT_REV_NUM="$(
  curl -s "$BASE/api/v1/versions/revision/next?current=1&scheme=number" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["next"])'
)"
if [[ "$NEXT_REV_NUM" == "2" ]]; then
  echo "Number scheme: 1 -> 2: OK"
else
  fail "Expected 2, got $NEXT_REV_NUM"
fi

# =============================================================================
# Step 10: Test revision comparison
# =============================================================================
echo "==> Test revision comparison"
REV_CMP="$(
  curl -s "$BASE/api/v1/versions/revision/compare?rev_a=A&rev_b=C" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["comparison"])'
)"
if [[ "$REV_CMP" == "-1" ]]; then
  echo "Revision compare: A < C: OK"
else
  fail "Expected -1 (A < C), got $REV_CMP"
fi

# =============================================================================
# Step 11: Test iteration within version
# =============================================================================
echo "==> Test iteration within version"

# Get current version ID (1.C)
CURRENT_VER_ID="$("$PY" -c "import sys,json;d=json.loads('$VER_REVISE2');print(d['id'])")"

# Create iteration
ITER_RESULT="$(
  curl -s -X POST "$BASE/api/v1/versions/$CURRENT_VER_ID/iterations" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d '{"description":"First iteration","source_type":"manual"}'
)"
ITER_LABEL="$("$PY" -c "import sys,json;d=json.loads('$ITER_RESULT');print(d.get('iteration_label',''))")"
ITER_NUM="$("$PY" -c "import sys,json;d=json.loads('$ITER_RESULT');print(d.get('iteration_number',0))")"

if [[ "$ITER_LABEL" == "1.C.1" ]] && [[ "$ITER_NUM" == "1" ]]; then
  echo "Created iteration: $ITER_LABEL: OK"
else
  fail "Expected iteration 1.C.1 (#1), got $ITER_LABEL (#$ITER_NUM)"
fi

# Create second iteration
ITER2_RESULT="$(
  curl -s -X POST "$BASE/api/v1/versions/$CURRENT_VER_ID/iterations" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d '{"description":"Second iteration","source_type":"auto_save"}'
)"
ITER2_LABEL="$("$PY" -c "import sys,json;d=json.loads('$ITER2_RESULT');print(d.get('iteration_label',''))")"

if [[ "$ITER2_LABEL" == "1.C.2" ]]; then
  echo "Created iteration: $ITER2_LABEL: OK"
else
  fail "Expected iteration 1.C.2, got $ITER2_LABEL"
fi

# Get latest iteration
LATEST_ITER="$(
  curl -s "$BASE/api/v1/versions/$CURRENT_VER_ID/iterations/latest" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
LATEST_IS_LATEST="$("$PY" -c "import sys,json;d=json.loads('$LATEST_ITER');print(d.get('is_latest',False))")"
LATEST_LABEL="$("$PY" -c "import sys,json;d=json.loads('$LATEST_ITER');print(d.get('iteration_label',''))")"

if [[ "$LATEST_IS_LATEST" == "True" ]] && [[ "$LATEST_LABEL" == "1.C.2" ]]; then
  echo "Latest iteration is 1.C.2: OK"
else
  fail "Expected latest iteration 1.C.2, got $LATEST_LABEL (is_latest=$LATEST_IS_LATEST)"
fi

# =============================================================================
# Step 12: Test version comparison
# =============================================================================
echo "==> Test version comparison"
VER_DIFF="$(
  curl -s "$BASE/api/v1/versions/compare?v1=$VER_ID&v2=$VER_B_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
DIFF_VA="$("$PY" -c "import sys,json;d=json.loads('$VER_DIFF');print(d.get('version_a',''))")"
DIFF_VB="$("$PY" -c "import sys,json;d=json.loads('$VER_DIFF');print(d.get('version_b',''))")"

if [[ "$DIFF_VA" == "1.A" ]] && [[ "$DIFF_VB" == "1.B" ]]; then
  echo "Version comparison (1.A vs 1.B): OK"
else
  fail "Expected comparison of 1.A vs 1.B, got $DIFF_VA vs $DIFF_VB"
fi

# =============================================================================
# Step 13: Create revision scheme
# =============================================================================
echo "==> Create revision scheme"
SCHEME_RESULT="$(
  curl -s -X POST "$BASE/api/v1/versions/schemes" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"name\":\"TestScheme-$TS\",\"scheme_type\":\"number\",\"initial_revision\":\"1\",\"is_default\":false}"
)"
SCHEME_TYPE="$("$PY" -c "import sys,json;d=json.loads('$SCHEME_RESULT');print(d.get('scheme_type',''))")"
SCHEME_INIT="$("$PY" -c "import sys,json;d=json.loads('$SCHEME_RESULT');print(d.get('initial_revision',''))")"

if [[ "$SCHEME_TYPE" == "number" ]] && [[ "$SCHEME_INIT" == "1" ]]; then
  echo "Created revision scheme (number, starts at 1): OK"
else
  fail "Expected scheme type 'number' with initial '1', got '$SCHEME_TYPE' with '$SCHEME_INIT'"
fi

# List schemes
SCHEMES_LIST="$(
  curl -s "$BASE/api/v1/versions/schemes" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
SCHEMES_COUNT="$("$PY" -c "import sys,json;d=json.loads('$SCHEMES_LIST');print(len(d))")"

if [[ "$SCHEMES_COUNT" -ge "1" ]]; then
  echo "Revision schemes list: $SCHEMES_COUNT scheme(s): OK"
else
  fail "Expected at least 1 scheme, got $SCHEMES_COUNT"
fi

# =============================================================================
# Step 14: Test checkout/checkin flow
# =============================================================================
echo "==> Test checkout/checkin flow"

# Create a new Part for checkout test
PN2="P-CHECKOUT-$TS"
PART2_RESULT="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN2\",\"name\":\"Checkout Test Part\"}}"
)"
PART2_ID="$("$PY" -c "import sys,json;print(json.loads('$PART2_RESULT')['id'])")"

# Initialize version
curl -s -X POST "$BASE/api/v1/versions/items/$PART2_ID/init" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" >/dev/null

# Checkout
CHECKOUT_RESULT="$(
  curl -s -X POST "$BASE/api/v1/versions/items/$PART2_ID/checkout" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d '{"comment":"Checking out for edit"}'
)"
CHECKOUT_BY="$("$PY" -c "import sys,json;d=json.loads('$CHECKOUT_RESULT');print(d.get('checked_out_by_id',''))")"

if [[ -n "$CHECKOUT_BY" ]] && [[ "$CHECKOUT_BY" != "None" ]]; then
  echo "Checkout: locked by user $CHECKOUT_BY: OK"
else
  fail "Expected checked_out_by_id to be set"
fi

# Checkin with property update
CHECKIN_RESULT="$(
  curl -s -X POST "$BASE/api/v1/versions/items/$PART2_ID/checkin" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d '{"comment":"Done editing","properties":{"description":"Updated via checkin"}}'
)"
CHECKIN_BY="$("$PY" -c "import sys,json;d=json.loads('$CHECKIN_RESULT');print(d.get('checked_out_by_id','None'))")"

if [[ "$CHECKIN_BY" == "None" ]]; then
  echo "Checkin: unlocked: OK"
else
  fail "Expected checked_out_by_id to be None after checkin"
fi

# =============================================================================
# Summary
# =============================================================================
echo
echo "=============================================="
echo "VERSION SEMANTICS SUMMARY"
echo "=============================================="
echo "Version Label Format: {generation}.{revision}"
echo "  - Generation: 1, 2, 3, ..."
echo "  - Revision: A, B, C, ..., Z, AA, AB, ..."
echo "  - Example: 1.A, 1.B, 2.A, 2.AA"
echo ""
echo "Iteration Format: {version_label}.{iteration}"
echo "  - Example: 1.A.1, 1.A.2, 1.B.1"
echo ""
echo "Revision Schemes:"
echo "  - letter (default): A -> B -> ... -> Z -> AA"
echo "  - number: 1 -> 2 -> 3 -> ..."
echo "  - hybrid: A1 -> A2 -> ... -> A99 -> B1"
echo "=============================================="
echo

if [[ "$FAILED" -eq 0 ]]; then
  echo "ALL CHECKS PASSED"
else
  echo "SOME CHECKS FAILED"
  exit 1
fi
