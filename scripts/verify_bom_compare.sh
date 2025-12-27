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
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null
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
EFFECTIVE_FROM="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

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
  -d "{\"child_id\":\"$CHILD_X\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"020\",\"refdes\":\"R1,R2\",\"effectivity_from\":\"$EFFECTIVE_FROM\"}" >/dev/null
$CURL -X POST "$API/bom/$PARENT_B/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_Z\",\"quantity\":1,\"uom\":\"EA\"}" >/dev/null
ok "BOM B created"

echo ""
echo "==> Create substitute for CHILD_X in BOM B"
SUB_PART_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CMP-S-$TS\",\"name\":\"Substitute $TS\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$SUB_PART_ID" ]]; then
  fail "Failed to create substitute part"
fi

TREE_RESP="$($CURL "$API/bom/$PARENT_B/tree?depth=1" "${HEADERS[@]}" "${AUTH[@]}")"
BOM_LINE_X="$(
  RESP_JSON="$TREE_RESP" CHILD_ID="$CHILD_X" "$PY" - <<'PY'
import os, json
data = json.loads(os.environ.get("RESP_JSON", "{}"))
child_id = os.environ.get("CHILD_ID")
for entry in data.get("children", []) or []:
    rel = entry.get("relationship") or {}
    child = entry.get("child") or {}
    if child.get("id") == child_id:
        print(rel.get("id") or "")
        raise SystemExit(0)
print("")
PY
)"
if [[ -z "$BOM_LINE_X" ]]; then
  fail "Failed to resolve BOM line for CHILD_X"
fi

SUB_RESP="$(
  $CURL -X POST "$API/bom/$BOM_LINE_X/substitutes" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"$SUB_PART_ID\",\"properties\":{\"rank\":1}}"
)"
SUB_ID="$(echo "$SUB_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("substitute_id",""))')"
if [[ -z "$SUB_ID" ]]; then
  echo "Response: $SUB_RESP"
  fail "Failed to add substitute to BOM line"
fi
ok "Substitute added: $SUB_ID"

echo ""
echo "==> Compare BOM"
RESP="$(
  $CURL "$API/bom/compare?left_type=item&left_id=$PARENT_A&right_type=item&right_id=$PARENT_B&max_levels=10&line_key=child_config&include_relationship_props=quantity,uom,find_num,refdes,effectivity_from,effectivity_to&include_substitutes=true&include_effectivity=true" \
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

if summary.get("changed_major", 0) < 1:
    raise SystemExit("expected >=1 changed_major")

target = None
for entry in changed:
    cid = entry.get("child_id") or (entry.get("child") or {}).get("id")
    if cid == "$CHILD_X":
        target = entry
        break
if not target:
    raise SystemExit("missing changed entry for CHILD_X")

diff_fields = {d.get("field") for d in (target.get("changes") or []) if d.get("field")}
missing = {"quantity", "find_num", "refdes", "substitutes", "effectivities"} - diff_fields
if missing:
    raise SystemExit(f"missing diff fields: {sorted(missing)}")

severity = target.get("severity")
if severity not in {"major"}:
    raise SystemExit(f"unexpected severity: {severity}")

line_key = target.get("line_key")
if not line_key:
    raise SystemExit("missing line_key in compare output")

before = target.get("before") or {}
after = target.get("after") or {}

def to_float(val):
    try:
        return float(val)
    except Exception:
        return None

if to_float(before.get("quantity")) != 1.0 or to_float(after.get("quantity")) != 2.0:
    raise SystemExit("quantity diff mismatch")
if str(before.get("find_num")) != "010" or str(after.get("find_num")) != "020":
    raise SystemExit("find_num diff mismatch")
before_ref = str(before.get("refdes"))
after_ref = str(after.get("refdes"))
if "R1" not in before_ref or "R1" not in after_ref or "R2" not in after_ref:
    raise SystemExit("refdes diff mismatch")

print("BOM Compare: OK")
PY

echo ""
echo "==> Compare BOM (compare_mode=only_product)"
RESP_ONLY="$(
  $CURL "$API/bom/compare?left_type=item&left_id=$PARENT_A&right_type=item&right_id=$PARENT_B&max_levels=10&compare_mode=only_product" \
    "${HEADERS[@]}" "${AUTH[@]}"
)"

RESP_JSON="$RESP_ONLY" "$PY" - <<PY
import os
import json

raw = os.environ.get("RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /bom/compare (only_product)")
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

if summary.get("changed", 0) != 0 or changed:
    raise SystemExit("only_product should not report changed entries")

if "$CHILD_Z" not in added_ids:
    raise SystemExit("only_product: expected CHILD_Z in added")
if "$CHILD_Y" not in removed_ids:
    raise SystemExit("only_product: expected CHILD_Y in removed")
if "$CHILD_X" in added_ids or "$CHILD_X" in removed_ids:
    raise SystemExit("only_product: CHILD_X should not be added/removed")

print("BOM Compare only_product: OK")
PY

echo ""
echo "==> Compare BOM (compare_mode=num_qty)"
RESP_NUM="$(
  $CURL "$API/bom/compare?left_type=item&left_id=$PARENT_A&right_type=item&right_id=$PARENT_B&max_levels=10&compare_mode=num_qty" \
    "${HEADERS[@]}" "${AUTH[@]}"
)"

RESP_JSON="$RESP_NUM" "$PY" - <<PY
import os
import json

raw = os.environ.get("RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /bom/compare (num_qty)")
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

if summary.get("changed", 0) != 0 or changed:
    raise SystemExit("num_qty should not report changed entries")

if "$CHILD_Z" not in added_ids:
    raise SystemExit("num_qty: expected CHILD_Z in added")
if "$CHILD_Y" not in removed_ids:
    raise SystemExit("num_qty: expected CHILD_Y in removed")
if "$CHILD_X" not in added_ids or "$CHILD_X" not in removed_ids:
    raise SystemExit("num_qty: expected CHILD_X in both added and removed")

print("BOM Compare num_qty: OK")
PY

echo ""
echo "==> Compare BOM (compare_mode=summarized)"
RESP_SUM="$(
  $CURL "$API/bom/compare?left_type=item&left_id=$PARENT_A&right_type=item&right_id=$PARENT_B&max_levels=10&compare_mode=summarized" \
    "${HEADERS[@]}" "${AUTH[@]}"
)"

RESP_JSON="$RESP_SUM" "$PY" - <<PY
import os
import json

raw = os.environ.get("RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /bom/compare (summarized)")
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

if summary.get("changed", len(changed)) < 1:
    raise SystemExit("summarized should report changed entries")
if "$CHILD_Z" not in added_ids:
    raise SystemExit("summarized: expected CHILD_Z in added")
if "$CHILD_Y" not in removed_ids:
    raise SystemExit("summarized: expected CHILD_Y in removed")
if "$CHILD_X" not in changed_ids:
    raise SystemExit("summarized: expected CHILD_X in changed")

target = None
for entry in changed:
    cid = entry.get("child_id") or (entry.get("child") or {}).get("id")
    if cid == "$CHILD_X":
        target = entry
        break
if not target:
    raise SystemExit("summarized: missing changed entry for CHILD_X")

diff_fields = {d.get("field") for d in (target.get("changes") or []) if d.get("field")}
if "quantity" not in diff_fields:
    raise SystemExit("summarized: expected quantity diff")
extra = diff_fields - {"quantity", "uom"}
if extra:
    raise SystemExit(f"summarized: unexpected diff fields: {sorted(extra)}")

print("BOM Compare summarized: OK")
PY

echo ""
echo "=============================================="
echo "BOM Compare Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
