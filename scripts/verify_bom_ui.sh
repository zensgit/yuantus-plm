#!/usr/bin/env bash
# =============================================================================
# BOM UI Verification
# Verifies: where-used, bom_compare (with child fields), substitutes list
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

printf "==============================================\n"
printf "BOM UI Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 200000))}"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id "$ADMIN_UID" --roles admin >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null
ok "Seeded identity/meta"

printf "\n==> Login as admin\n"
ADMIN_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
ADMIN_AUTH=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

TS="$(date +%s)"
LEFT_NUM="BOMUI-L-$TS"
RIGHT_NUM="BOMUI-R-$TS"
CHILD_L_NUM="BOMUI-CL-$TS"
CHILD_R_NUM="BOMUI-CR-$TS"
SUB_NUM="BOMUI-SUB-$TS"

create_part() {
  local num="$1"
  local name="$2"
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$num\",\"name\":\"$name\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
}

printf "\n==> Create Parts\n"
LEFT_ID="$(create_part "$LEFT_NUM" "BOM UI Left $TS")"
RIGHT_ID="$(create_part "$RIGHT_NUM" "BOM UI Right $TS")"
CHILD_L_ID="$(create_part "$CHILD_L_NUM" "BOM UI Child L $TS")"
CHILD_R_ID="$(create_part "$CHILD_R_NUM" "BOM UI Child R $TS")"
SUB_ID="$(create_part "$SUB_NUM" "BOM UI Substitute $TS")"

if [[ -z "$LEFT_ID" || -z "$RIGHT_ID" || -z "$CHILD_L_ID" || -z "$CHILD_R_ID" || -z "$SUB_ID" ]]; then
  fail "Failed to create BOM UI parts"
fi
ok "Created Parts"

printf "\n==> Add children to BOM\n"
REL_L_RESP="$(
  $CURL -X POST "$API/bom/$LEFT_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_L_ID\",\"quantity\":2,\"uom\":\"EA\"}"
)"
REL_L_ID="$(echo "$REL_L_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_L_ID" ]]; then
  echo "Response: $REL_L_RESP"
  fail "Failed to add child to left BOM"
fi

REL_R_RESP="$(
  $CURL -X POST "$API/bom/$RIGHT_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_R_ID\",\"quantity\":1,\"uom\":\"EA\"}"
)"
REL_R_ID="$(echo "$REL_R_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_R_ID" ]]; then
  echo "Response: $REL_R_RESP"
  fail "Failed to add child to right BOM"
fi
ok "Added BOM children"

printf "\n==> Add substitute to BOM line\n"
SUB_RESP="$(
  $CURL -X POST "$API/bom/$REL_L_ID/substitutes" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"$SUB_ID\",\"properties\":{\"rank\":1}}"
)"
SUB_REL_ID="$(echo "$SUB_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("substitute_id",""))')"
if [[ -z "$SUB_REL_ID" ]]; then
  echo "Response: $SUB_RESP"
  fail "Failed to add substitute"
fi
ok "Added substitute: $SUB_REL_ID"

printf "\n==> Where-used\n"
WHERE_USED_RESP="$(
  $CURL "$API/bom/$CHILD_L_ID/where-used?recursive=false" "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

printf "\n==> BOM compare (include child fields)\n"
COMPARE_RESP="$(
  $CURL "$API/bom/compare?left_type=item&left_id=$LEFT_ID&right_type=item&right_id=$RIGHT_ID&max_levels=5&compare_mode=only_product&include_child_fields=true" \
    "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

printf "\n==> Substitutes list\n"
SUB_LIST_RESP="$(
  $CURL "$API/bom/$REL_L_ID/substitutes" "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

WHERE_USED_JSON="$WHERE_USED_RESP" \
COMPARE_JSON="$COMPARE_RESP" \
SUB_LIST_JSON="$SUB_LIST_RESP" \
LEFT_NUM="$LEFT_NUM" \
CHILD_L_NUM="$CHILD_L_NUM" \
SUB_NUM="$SUB_NUM" \
"$PY" - <<'PY'
import os
import json

where_used = json.loads(os.environ["WHERE_USED_JSON"])
compare = json.loads(os.environ["COMPARE_JSON"])
subs = json.loads(os.environ["SUB_LIST_JSON"])

left_num = os.environ["LEFT_NUM"]
child_num = os.environ["CHILD_L_NUM"]
sub_num = os.environ["SUB_NUM"]

parents = where_used.get("parents") or []
if not parents:
    raise SystemExit("where-used returned no parents")
parent = parents[0].get("parent") or {}
parent_number = parent.get("item_number") or (parent.get("properties") or {}).get("item_number")
if parent_number != left_num:
    raise SystemExit(f"where-used parent item_number mismatch: {parent_number} != {left_num}")

summary = compare.get("summary") or {}
if summary.get("added", 0) + summary.get("removed", 0) + summary.get("changed", 0) == 0:
    raise SystemExit("bom compare returned no differences")

added = compare.get("added") or []
if not added:
    raise SystemExit("bom compare added list empty")
first = added[0]
child = first.get("child") or {}
child_number = child.get("item_number")
if not child_number:
    raise SystemExit("bom compare missing child fields")

sub_list = subs.get("substitutes") or []
if not sub_list:
    raise SystemExit("substitutes list empty")
sub_entry = sub_list[0]
sub_part = sub_entry.get("substitute_part") or sub_entry.get("part") or {}
sub_number = sub_part.get("item_number") or (sub_part.get("properties") or {}).get("item_number")
if sub_number != sub_num:
    raise SystemExit(f"substitute item_number mismatch: {sub_number} != {sub_num}")

print("BOM UI endpoints: OK")
PY

printf "\n==============================================\n"
printf "BOM UI Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
