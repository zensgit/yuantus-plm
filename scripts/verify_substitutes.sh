#!/usr/bin/env bash
# =============================================================================
# BOM Substitutes Verification Script
# Verifies: add/list/remove substitutes on a BOM line
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

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

printf "==============================================\n"
printf "BOM Substitutes Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null
ok "Seeded identity/meta"

printf "\n==> Login as admin\n"
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

printf "\n==> Create parent/child/substitute items\n"
PARENT_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUB-A-$TS\",\"name\":\"Substitute Parent\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
CHILD_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUB-C-$TS\",\"name\":\"Primary Child\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
SUB1_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUB-S1-$TS\",\"name\":\"Substitute 1\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
SUB2_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUB-S2-$TS\",\"name\":\"Substitute 2\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"

if [[ -z "$PARENT_ID" || -z "$CHILD_ID" || -z "$SUB1_ID" || -z "$SUB2_ID" ]]; then
  fail "Failed to create items"
fi
ok "Created parent=$PARENT_ID child=$CHILD_ID substitutes=$SUB1_ID,$SUB2_ID"

printf "\n==> Create BOM line (parent -> child)\n"
BOM_RESP="$(
  $CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":1,\"uom\":\"EA\"}"
)"
BOM_LINE_ID="$(echo "$BOM_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$BOM_LINE_ID" ]]; then
  echo "Response: $BOM_RESP"
  fail "Failed to create BOM line"
fi
ok "Created BOM line: $BOM_LINE_ID"

printf "\n==> Add substitute 1\n"
ADD1_RESP="$(
  $CURL -X POST "$API/bom/$BOM_LINE_ID/substitutes" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"$SUB1_ID\",\"properties\":{\"rank\":1,\"note\":\"alt-1\"}}"
)"
ADD1_ID="$(echo "$ADD1_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("substitute_id",""))')"
if [[ -z "$ADD1_ID" ]]; then
  echo "Response: $ADD1_RESP"
  fail "Failed to add substitute 1"
fi
ok "Added substitute 1: $ADD1_ID"

printf "\n==> List substitutes (expect 1)\n"
LIST1_RESP="$(
  $CURL "$API/bom/$BOM_LINE_ID/substitutes" "${HEADERS[@]}" "${AUTH[@]}"
)"
LIST1_COUNT="$(echo "$LIST1_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("count",0))')"
if [[ "$LIST1_COUNT" -ne 1 ]]; then
  echo "Response: $LIST1_RESP"
  fail "Expected 1 substitute, got $LIST1_COUNT"
fi
ok "List count=1"

printf "\n==> Add substitute 2\n"
ADD2_RESP="$(
  $CURL -X POST "$API/bom/$BOM_LINE_ID/substitutes" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"$SUB2_ID\",\"properties\":{\"rank\":2}}"
)"
ADD2_ID="$(echo "$ADD2_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("substitute_id",""))')"
if [[ -z "$ADD2_ID" ]]; then
  echo "Response: $ADD2_RESP"
  fail "Failed to add substitute 2"
fi
ok "Added substitute 2: $ADD2_ID"

printf "\n==> Duplicate add (should 400)\n"
DUP_FILE="$TMP_DIR/dup.json"
DUP_CODE="$(curl -s -o "$DUP_FILE" -w '%{http_code}' \
  -X POST "$API/bom/$BOM_LINE_ID/substitutes" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"substitute_item_id\":\"$SUB2_ID\"}")"
if [[ "$DUP_CODE" != "400" ]]; then
  echo "Response: $(cat "$DUP_FILE")"
  fail "Expected 400 for duplicate add, got $DUP_CODE"
fi
ok "Duplicate add blocked (400)"

printf "\n==> Remove substitute 1\n"
DEL1_RESP="$(
  $CURL -X DELETE "$API/bom/$BOM_LINE_ID/substitutes/$ADD1_ID" "${HEADERS[@]}" "${AUTH[@]}"
)"
DEL1_OK="$(echo "$DEL1_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("ok",False))')"
if [[ "$DEL1_OK" != "True" ]]; then
  echo "Response: $DEL1_RESP"
  fail "Failed to remove substitute 1"
fi
ok "Removed substitute 1"

printf "\n==> List substitutes (expect 1 remaining)\n"
LIST2_RESP="$(
  $CURL "$API/bom/$BOM_LINE_ID/substitutes" "${HEADERS[@]}" "${AUTH[@]}"
)"
LIST2_COUNT="$(echo "$LIST2_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("count",0))')"
if [[ "$LIST2_COUNT" -ne 1 ]]; then
  echo "Response: $LIST2_RESP"
  fail "Expected 1 substitute remaining, got $LIST2_COUNT"
fi
ok "List count=1 after delete"

printf "\n==============================================\n"
printf "BOM Substitutes Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
