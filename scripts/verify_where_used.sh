#!/usr/bin/env bash
# =============================================================================
# Where-Used API Verification Script
# Verifies: BOM hierarchy creation → where-used query → recursive traversal
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

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

echo "=============================================="
echo "Where-Used API Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
fail() { echo "FAIL: $1"; exit 1; }
ok() { echo "OK: $1"; }

check_http() {
  local expected="$1"
  local actual="$2"
  local msg="$3"
  if [[ "$actual" == "$expected" ]]; then
    ok "$msg (HTTP $actual)"
  else
    fail "$msg - expected HTTP $expected, got $actual"
  fi
}

# -----------------------------------------------------------------------------
# 1) Setup: Seed identity and meta
# -----------------------------------------------------------------------------
echo ""
echo "==> Seed identity (admin user)"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
ok "Identity seeded"

echo ""
echo "==> Seed meta schema"
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || "$CLI" seed-meta >/dev/null
ok "Meta schema seeded"

# -----------------------------------------------------------------------------
# 2) Login
# -----------------------------------------------------------------------------
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
ok "Admin login"
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")

# -----------------------------------------------------------------------------
# 3) Create test items for BOM hierarchy
# -----------------------------------------------------------------------------
echo ""
echo "==> Create test items for BOM hierarchy"

TS="$(date +%s)"

# Create assembly (top level)
ASSEMBLY_RESP="$(
  $CURL -X POST "$API/aml/apply" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WU-ASSY-$TS\",\"name\":\"Assembly for Where-Used Test $TS\"}}"
)"
ASSEMBLY_ID="$(echo "$ASSEMBLY_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("id","") or "")')"
if [[ -z "$ASSEMBLY_ID" ]]; then
  echo "Response: $ASSEMBLY_RESP"
  fail "Could not create assembly"
fi
ok "Created assembly: $ASSEMBLY_ID"

# Create sub-assembly (middle level)
SUBASSY_RESP="$(
  $CURL -X POST "$API/aml/apply" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WU-SUBASSY-$TS\",\"name\":\"Sub-Assembly for Where-Used Test $TS\"}}"
)"
SUBASSY_ID="$(echo "$SUBASSY_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("id","") or "")')"
if [[ -z "$SUBASSY_ID" ]]; then
  echo "Response: $SUBASSY_RESP"
  fail "Could not create sub-assembly"
fi
ok "Created sub-assembly: $SUBASSY_ID"

# Create component (leaf level)
COMPONENT_RESP="$(
  $CURL -X POST "$API/aml/apply" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WU-COMP-$TS\",\"name\":\"Component for Where-Used Test $TS\"}}"
)"
COMPONENT_ID="$(echo "$COMPONENT_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("id","") or "")')"
if [[ -z "$COMPONENT_ID" ]]; then
  echo "Response: $COMPONENT_RESP"
  fail "Could not create component"
fi
ok "Created component: $COMPONENT_ID"

# Create another assembly that also uses the component
ASSEMBLY2_RESP="$(
  $CURL -X POST "$API/aml/apply" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WU-ASSY2-$TS\",\"name\":\"Second Assembly for Where-Used Test $TS\"}}"
)"
ASSEMBLY2_ID="$(echo "$ASSEMBLY2_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("id","") or "")')"
if [[ -z "$ASSEMBLY2_ID" ]]; then
  echo "Response: $ASSEMBLY2_RESP"
  fail "Could not create second assembly"
fi
ok "Created second assembly: $ASSEMBLY2_ID"

# -----------------------------------------------------------------------------
# 4) Build BOM hierarchy
# -----------------------------------------------------------------------------
echo ""
echo "==> Build BOM hierarchy"

# Assembly -> Sub-Assembly
BOM1_RESP="$(
  $CURL -X POST "$API/bom/$ASSEMBLY_ID/children" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$SUBASSY_ID\",\"quantity\":1,\"uom\":\"EA\"}"
)"
BOM1_OK="$(echo "$BOM1_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("ok",False))')"
if [[ "$BOM1_OK" != "True" ]]; then
  echo "Response: $BOM1_RESP"
  fail "Could not add sub-assembly to assembly"
fi
ok "Added sub-assembly to assembly"

# Sub-Assembly -> Component
BOM2_RESP="$(
  $CURL -X POST "$API/bom/$SUBASSY_ID/children" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$COMPONENT_ID\",\"quantity\":2,\"uom\":\"EA\"}"
)"
BOM2_OK="$(echo "$BOM2_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("ok",False))')"
if [[ "$BOM2_OK" != "True" ]]; then
  echo "Response: $BOM2_RESP"
  fail "Could not add component to sub-assembly"
fi
ok "Added component to sub-assembly"

# Assembly2 -> Component (direct usage)
BOM3_RESP="$(
  $CURL -X POST "$API/bom/$ASSEMBLY2_ID/children" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$COMPONENT_ID\",\"quantity\":4,\"uom\":\"EA\"}"
)"
BOM3_OK="$(echo "$BOM3_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("ok",False))')"
if [[ "$BOM3_OK" != "True" ]]; then
  echo "Response: $BOM3_RESP"
  fail "Could not add component to second assembly"
fi
ok "Added component to second assembly"

echo ""
echo "BOM Structure:"
echo "  ASSEMBLY ($ASSEMBLY_ID)"
echo "    └── SUB-ASSEMBLY ($SUBASSY_ID)"
echo "          └── COMPONENT ($COMPONENT_ID)"
echo "  ASSEMBLY2 ($ASSEMBLY2_ID)"
echo "    └── COMPONENT ($COMPONENT_ID)"

# -----------------------------------------------------------------------------
# 5) Test Where-Used: Direct parents only
# -----------------------------------------------------------------------------
echo ""
echo "==> Test Where-Used (non-recursive)"

WU_RESP="$(
  $CURL "$API/bom/$COMPONENT_ID/where-used?recursive=false" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"

WU_COUNT="$(echo "$WU_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("count",0))')"
WU_ITEM_ID="$(echo "$WU_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("item_id",""))')"

echo "Where-used response:"
echo "  item_id: $WU_ITEM_ID"
echo "  count: $WU_COUNT"

if [[ "$WU_COUNT" -ne 2 ]]; then
  echo "Response: $WU_RESP"
  fail "Expected 2 direct parents, got $WU_COUNT"
fi
ok "Non-recursive where-used: found 2 direct parents"

# Verify the parent IDs
PARENT_IDS="$(echo "$WU_RESP" | "$PY" -c '
import sys,json
d = json.load(sys.stdin)
parents = d.get("parents", [])
for p in parents:
    parent = p.get("parent", {})
    print(parent.get("id", ""))
')"

echo "Parent IDs found:"
echo "$PARENT_IDS" | while read -r pid; do
  if [[ -n "$pid" ]]; then
    echo "  - $pid"
  fi
done

# -----------------------------------------------------------------------------
# 6) Test Where-Used: Recursive
# -----------------------------------------------------------------------------
echo ""
echo "==> Test Where-Used (recursive)"

WU_REC_RESP="$(
  $CURL "$API/bom/$COMPONENT_ID/where-used?recursive=true&max_levels=5" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"

WU_REC_COUNT="$(echo "$WU_REC_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("count",0))')"

echo "Recursive where-used response:"
echo "  count: $WU_REC_COUNT"

# Should find: Sub-Assembly (level 1), Assembly (level 2), Assembly2 (level 1)
if [[ "$WU_REC_COUNT" -lt 2 ]]; then
  echo "Response: $WU_REC_RESP"
  fail "Expected at least 2 parents in recursive mode, got $WU_REC_COUNT"
fi
ok "Recursive where-used: found $WU_REC_COUNT parents"

# Show levels
echo "Parents by level:"
echo "$WU_REC_RESP" | "$PY" -c '
import sys,json
d = json.load(sys.stdin)
parents = d.get("parents", [])
for p in parents:
    parent = p.get("parent", {})
    level = p.get("level", 0)
    name = parent.get("name", parent.get("item_number", "unknown"))
    print(f"  Level {level}: {name}")
'

# -----------------------------------------------------------------------------
# 7) Test Where-Used on item with no parents
# -----------------------------------------------------------------------------
echo ""
echo "==> Test Where-Used on top-level item (no parents)"

WU_TOP_RESP="$(
  $CURL "$API/bom/$ASSEMBLY_ID/where-used?recursive=false" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"

WU_TOP_COUNT="$(echo "$WU_TOP_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("count",0))')"

if [[ "$WU_TOP_COUNT" -ne 0 ]]; then
  echo "Response: $WU_TOP_RESP"
  fail "Expected 0 parents for top-level assembly, got $WU_TOP_COUNT"
fi
ok "Top-level item has no parents (count=0)"

# -----------------------------------------------------------------------------
# 8) Test Where-Used on non-existent item
# -----------------------------------------------------------------------------
echo ""
echo "==> Test Where-Used on non-existent item"

WU_404_HTTP="$(
  $CURL -o /dev/null -w '%{http_code}' \
    "$API/bom/non-existent-id/where-used" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"

check_http "404" "$WU_404_HTTP" "Non-existent item returns 404"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "Where-Used API Verification Complete"
echo "=============================================="
echo ""
echo "Summary:"
echo "  - BOM hierarchy creation: OK"
echo "  - Non-recursive where-used: OK (found 2 direct parents)"
echo "  - Recursive where-used: OK (found $WU_REC_COUNT total parents)"
echo "  - Top-level item (no parents): OK"
echo "  - Non-existent item handling: OK (404)"
echo ""
echo "ALL CHECKS PASSED"
exit 0
