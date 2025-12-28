#!/usr/bin/env bash
# =============================================================================
# Equivalent Parts Verification Script
# Verifies: add/list/remove equivalent part relationships
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
printf "Equivalent Parts Verification\n"
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

printf "\n==> Create test parts\n"
PART_A="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EQ-A-$TS\",\"name\":\"Equivalent A\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
PART_B="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EQ-B-$TS\",\"name\":\"Equivalent B\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
PART_C="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EQ-C-$TS\",\"name\":\"Equivalent C\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"

if [[ -z "$PART_A" || -z "$PART_B" || -z "$PART_C" ]]; then
  fail "Failed to create parts"
fi
ok "Created parts A=$PART_A B=$PART_B C=$PART_C"

printf "\n==> Add equivalent A <-> B\n"
ADD_AB_RESP="$(
  $CURL -X POST "$API/items/$PART_A/equivalents" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"equivalent_item_id\":\"$PART_B\",\"properties\":{\"rank\":1,\"note\":\"primary\"}}"
)"
EQ_AB_ID="$(echo "$ADD_AB_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("equivalent_id",""))')"
if [[ -z "$EQ_AB_ID" ]]; then
  echo "Response: $ADD_AB_RESP"
  fail "Failed to add equivalent A-B"
fi
ok "Added equivalent A-B: $EQ_AB_ID"

printf "\n==> Add equivalent A <-> C\n"
ADD_AC_RESP="$(
  $CURL -X POST "$API/items/$PART_A/equivalents" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"equivalent_item_id\":\"$PART_C\",\"properties\":{\"rank\":2}}"
)"
EQ_AC_ID="$(echo "$ADD_AC_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("equivalent_id",""))')"
if [[ -z "$EQ_AC_ID" ]]; then
  echo "Response: $ADD_AC_RESP"
  fail "Failed to add equivalent A-C"
fi
ok "Added equivalent A-C: $EQ_AC_ID"

printf "\n==> List equivalents for A (expect 2)\n"
LIST_A_RESP="$($CURL "$API/items/$PART_A/equivalents" "${HEADERS[@]}" "${AUTH[@]}")"
LIST_A_COUNT="$(echo "$LIST_A_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("count",0))')"
if [[ "$LIST_A_COUNT" -ne 2 ]]; then
  echo "Response: $LIST_A_RESP"
  fail "Expected 2 equivalents for A, got $LIST_A_COUNT"
fi
LIST_A_OK="$(
  LIST_JSON="$LIST_A_RESP" EXPECT1="$PART_B" EXPECT2="$PART_C" "$PY" - <<'PY'
import json
import os

data = json.loads(os.environ.get("LIST_JSON", "{}"))
ids = [e.get("equivalent_item_id") for e in data.get("equivalents", [])]
expect1 = os.environ.get("EXPECT1")
expect2 = os.environ.get("EXPECT2")
print("1" if expect1 in ids and expect2 in ids else "0")
PY
)"
if [[ "$LIST_A_OK" != "1" ]]; then
  echo "Response: $LIST_A_RESP"
  fail "Expected equivalents for A to include B and C"
fi
ok "List A count=2 with B,C"

printf "\n==> List equivalents for B (expect 1: A)\n"
LIST_B_RESP="$($CURL "$API/items/$PART_B/equivalents" "${HEADERS[@]}" "${AUTH[@]}")"
LIST_B_COUNT="$(echo "$LIST_B_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("count",0))')"
if [[ "$LIST_B_COUNT" -ne 1 ]]; then
  echo "Response: $LIST_B_RESP"
  fail "Expected 1 equivalent for B, got $LIST_B_COUNT"
fi
LIST_B_OK="$(
  LIST_JSON="$LIST_B_RESP" EXPECT="$PART_A" "$PY" - <<'PY'
import json
import os

data = json.loads(os.environ.get("LIST_JSON", "{}"))
ids = [e.get("equivalent_item_id") for e in data.get("equivalents", [])]
expect = os.environ.get("EXPECT")
print("1" if expect in ids else "0")
PY
)"
if [[ "$LIST_B_OK" != "1" ]]; then
  echo "Response: $LIST_B_RESP"
  fail "Expected B equivalents to include A"
fi
ok "List B count=1 with A"

printf "\n==> Duplicate add (B -> A, expect 400)\n"
DUP_FILE="$TMP_DIR/dup.json"
DUP_CODE="$(curl -s -o "$DUP_FILE" -w '%{http_code}' \
  -X POST "$API/items/$PART_B/equivalents" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"equivalent_item_id\":\"$PART_A\"}")"
if [[ "$DUP_CODE" != "400" ]]; then
  echo "Response: $(cat "$DUP_FILE")"
  fail "Expected 400 for duplicate add, got $DUP_CODE"
fi
ok "Duplicate add blocked (400)"

printf "\n==> Self add (A -> A, expect 400)\n"
SELF_FILE="$TMP_DIR/self.json"
SELF_CODE="$(curl -s -o "$SELF_FILE" -w '%{http_code}' \
  -X POST "$API/items/$PART_A/equivalents" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"equivalent_item_id\":\"$PART_A\"}")"
if [[ "$SELF_CODE" != "400" ]]; then
  echo "Response: $(cat "$SELF_FILE")"
  fail "Expected 400 for self-equivalence, got $SELF_CODE"
fi
ok "Self-equivalence blocked (400)"

printf "\n==> Remove equivalent A-B\n"
DEL_AB_RESP="$(
  $CURL -X DELETE "$API/items/$PART_A/equivalents/$EQ_AB_ID" "${HEADERS[@]}" "${AUTH[@]}"
)"
DEL_OK="$(echo "$DEL_AB_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("ok",False))')"
if [[ "$DEL_OK" != "True" ]]; then
  echo "Response: $DEL_AB_RESP"
  fail "Failed to remove equivalent A-B"
fi
ok "Removed equivalent A-B"

printf "\n==> List equivalents for B (expect 0)\n"
LIST_B2_RESP="$($CURL "$API/items/$PART_B/equivalents" "${HEADERS[@]}" "${AUTH[@]}")"
LIST_B2_COUNT="$(echo "$LIST_B2_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("count",0))')"
if [[ "$LIST_B2_COUNT" -ne 0 ]]; then
  echo "Response: $LIST_B2_RESP"
  fail "Expected 0 equivalents for B after delete, got $LIST_B2_COUNT"
fi
ok "List B count=0"

printf "\n==> List equivalents for A (expect 1)\n"
LIST_A2_RESP="$($CURL "$API/items/$PART_A/equivalents" "${HEADERS[@]}" "${AUTH[@]}")"
LIST_A2_COUNT="$(echo "$LIST_A2_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("count",0))')"
if [[ "$LIST_A2_COUNT" -ne 1 ]]; then
  echo "Response: $LIST_A2_RESP"
  fail "Expected 1 equivalent for A after delete, got $LIST_A2_COUNT"
fi
ok "List A count=1"

printf "\n==============================================\n"
printf "Equivalent Parts Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
