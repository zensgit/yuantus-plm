#!/usr/bin/env bash
# =============================================================================
# BOM Compare Verification Script
# Verifies: added/removed/changed BOM lines between two parents
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

fail() { echo "FAIL: $1"; exit 1; }
ok() { echo "OK: $1"; }

echo "=============================================="
echo "BOM Compare Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
"$CLI" seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login as admin"
TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH=(-H "Authorization: Bearer $TOKEN")
ok "Admin login"

TS="$(date +%s)"

echo ""
echo "==> Create parent items"
PARENT_A="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-A-$TS\",\"name\":\"Compare A\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
PARENT_B="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-B-$TS\",\"name\":\"Compare B\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$PARENT_A" || -z "$PARENT_B" ]]; then
  fail "Failed to create parent items"
fi
ok "Created parents: A=$PARENT_A, B=$PARENT_B"

echo ""
echo "==> Create child items"
CHILD_X="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-X-$TS\",\"name\":\"Child X\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
CHILD_Y="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-Y-$TS\",\"name\":\"Child Y\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
CHILD_Z="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-Z-$TS\",\"name\":\"Child Z\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$CHILD_X" || -z "$CHILD_Y" || -z "$CHILD_Z" ]]; then
  fail "Failed to create child items"
fi
ok "Created children: X=$CHILD_X, Y=$CHILD_Y, Z=$CHILD_Z"

echo ""
echo "==> Build BOM A (baseline)"
$CURL -X POST "$API/bom/$PARENT_A/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_X\",\"quantity\":1,\"uom\":\"EA\",\"find_num\":\"010\",\"refdes\":\"R1\"}" >/dev/null
$CURL -X POST "$API/bom/$PARENT_A/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_Y\",\"quantity\":1,\"uom\":\"EA\"}" >/dev/null
ok "BOM A created"

echo ""
echo "==> Build BOM B (changed + added)"
$CURL -X POST "$API/bom/$PARENT_B/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_X\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"020\",\"refdes\":\"R1,R2\"}" >/dev/null
$CURL -X POST "$API/bom/$PARENT_B/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_Z\",\"quantity\":1,\"uom\":\"EA\"}" >/dev/null
ok "BOM B created"

echo ""
echo "==> Compare BOM"
RESP="$(
  $CURL "$API/bom/compare?left_type=item&left_id=$PARENT_A&right_type=item&right_id=$PARENT_B&max_levels=10&include_relationship_props=quantity,uom,find_num,refdes" \
    "${HEADERS[@]}" "${AUTH[@]}"
)"

RESP_JSON="$RESP" "$PY" - <<PY
import os
import json

raw = os.environ.get("RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /bom/compare")
d = json.loads(raw)
summary = d.get("summary", {})
added = d.get("added", [])
removed = d.get("removed", [])
changed = d.get("changed", [])

def ids(entries):
    out = set()
    for e in entries:
        cid = e.get("child_id")
        if not cid:
            child = e.get("child") or {}
            cid = child.get("id")
        if cid:
            out.add(cid)
    return out

added_ids = ids(added)
removed_ids = ids(removed)
changed_ids = ids(changed)

assert (summary.get("added", len(added)) >= 1), "expected >=1 added"
assert (summary.get("removed", len(removed)) >= 1), "expected >=1 removed"
assert (summary.get("changed", len(changed)) >= 1), "expected >=1 changed"

assert "$CHILD_Z" in added_ids, "expected CHILD_Z in added"
assert "$CHILD_Y" in removed_ids, "expected CHILD_Y in removed"
assert "$CHILD_X" in changed_ids, "expected CHILD_X in changed"

print("BOM Compare: OK")
PY

echo ""
echo "=============================================="
echo "BOM Compare Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
