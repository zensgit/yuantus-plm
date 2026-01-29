#!/usr/bin/env bash
# =============================================================================
# S12 Configuration/Variant BOM Verification
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

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

# Seed identity/meta
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null

# Login
ADMIN_TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"

# Create option sets
COLOR_SET_ID="$(
  curl -s -X POST "$BASE/api/v1/config/option-sets" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d '{"name":"Color","label":"Color"}' \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
VOLT_SET_ID="$(
  curl -s -X POST "$BASE/api/v1/config/option-sets" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d '{"name":"Voltage","label":"Voltage"}' \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

# Add options
curl -s -X POST "$BASE/api/v1/config/option-sets/$COLOR_SET_ID/options" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"key":"Red","label":"Red","value":"Red","is_default":true}' >/dev/null
curl -s -X POST "$BASE/api/v1/config/option-sets/$COLOR_SET_ID/options" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"key":"Blue","label":"Blue","value":"Blue"}' >/dev/null
curl -s -X POST "$BASE/api/v1/config/option-sets/$VOLT_SET_ID/options" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"key":"110V","label":"110V","value":"110"}' >/dev/null
curl -s -X POST "$BASE/api/v1/config/option-sets/$VOLT_SET_ID/options" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"key":"220V","label":"220V","value":"220"}' >/dev/null

# Create parent/child items
PARENT_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-P-$TS\",\"name\":\"Config Parent\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD1_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-C1-$TS\",\"name\":\"Config Child 1\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD2_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-C2-$TS\",\"name\":\"Config Child 2\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD3_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-C3-$TS\",\"name\":\"Config Child 3\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD4_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-C4-$TS\",\"name\":\"Config Child 4\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD5_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-C5-$TS\",\"name\":\"Config Child 5\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD6_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-C6-$TS\",\"name\":\"Config Child 6\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD7_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-C7-$TS\",\"name\":\"Config Child 7\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

# Add BOM line with config condition
curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"child_id":"'$CHILD1_ID'","quantity":1,"uom":"EA","config_condition":{"option":"Color","value":"Red"}}' \
  >/dev/null

curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"child_id":"'$CHILD2_ID'","quantity":1,"uom":"EA","config_condition":{"option":"Voltage","op":"gte","value":200}}' \
  >/dev/null

curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"child_id":"'$CHILD3_ID'","quantity":1,"uom":"EA","config_condition":{"option":"Features","op":"contains","value":"Cooling"}}' \
  >/dev/null

curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"child_id":"'$CHILD4_ID'","quantity":1,"uom":"EA","config_condition":{"option":"Color","op":"ne","value":"Blue"}}' \
  >/dev/null

curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"child_id":"'$CHILD5_ID'","quantity":1,"uom":"EA","config_condition":{"option":"Region","missing":true}}' \
  >/dev/null

curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"child_id":"'$CHILD6_ID'","quantity":1,"uom":"EA","config_condition":{"option":"Region","exists":true}}' \
  >/dev/null

curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"child_id":"'$CHILD7_ID'","quantity":1,"uom":"EA","config_condition":"Voltage>=200;Color=Red"}' \
  >/dev/null

CONFIG_OK="$($PY - <<'PY'
import json,urllib.parse
print(urllib.parse.quote(json.dumps({"Color":"Red","Voltage":"220","Features":["Cooling","Fast"]})))
PY
)"
CONFIG_BAD="$($PY - <<'PY'
import json,urllib.parse
print(urllib.parse.quote(json.dumps({"Color":"Blue","Voltage":"110","Features":["Fast"],"Region":"US"})))
PY
)"
CONFIG_REGION="$($PY - <<'PY'
import json,urllib.parse
print(urllib.parse.quote(json.dumps({"Region":"US"})))
PY
)"
CONFIG_BLUE="$($PY - <<'PY'
import json,urllib.parse
print(urllib.parse.quote(json.dumps({"Color":"Blue","Voltage":"110","Features":["Fast"]})))
PY
)"

# Expect child when config matches
COUNT_OK="$(
  curl -s "$BASE/api/v1/bom/$PARENT_ID/tree?config=$CONFIG_OK" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children", [])))'
)"
if [[ "$COUNT_OK" != "6" ]]; then
  fail "Expected 6 children for matching config, got $COUNT_OK"
fi

# Expect only Region exists line when Region is provided
COUNT_BAD="$(
  curl -s "$BASE/api/v1/bom/$PARENT_ID/tree?config=$CONFIG_BAD" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children", [])))'
)"
if [[ "$COUNT_BAD" != "1" ]]; then
  fail "Expected 1 child for Region exists config, got $COUNT_BAD"
fi

COUNT_REGION="$(
  curl -s "$BASE/api/v1/bom/$PARENT_ID/tree?config=$CONFIG_REGION" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children", [])))'
)"
if [[ "$COUNT_REGION" != "1" ]]; then
  fail "Expected 1 child for Region-only config, got $COUNT_REGION"
fi

COUNT_BLUE="$(
  curl -s "$BASE/api/v1/bom/$PARENT_ID/tree?config=$CONFIG_BLUE" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children", [])))'
)"
if [[ "$COUNT_BLUE" != "1" ]]; then
  fail "Expected 1 child for Blue config (missing Region), got $COUNT_BLUE"
fi

# Expect child when no config is supplied
COUNT_DEFAULT="$(
  curl -s "$BASE/api/v1/bom/$PARENT_ID/tree" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children", [])))'
)"
if [[ "$COUNT_DEFAULT" != "7" ]]; then
  fail "Expected 7 children without config filter, got $COUNT_DEFAULT"
fi

echo "ALL CHECKS PASSED"
