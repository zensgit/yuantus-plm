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
CHILD_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-C-$TS\",\"name\":\"Config Child\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

# Add BOM line with config condition
curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"child_id":"'$CHILD_ID'","quantity":1,"uom":"EA","config_condition":{"all":[{"option":"Color","value":"Red"},{"option":"Voltage","value":"220"}]}}' \
  >/dev/null

CONFIG_OK="$($PY - <<'PY'
import json,urllib.parse
print(urllib.parse.quote(json.dumps({"Color":"Red","Voltage":"220"})))
PY
)"
CONFIG_BAD="$($PY - <<'PY'
import json,urllib.parse
print(urllib.parse.quote(json.dumps({"Color":"Blue","Voltage":"110"})))
PY
)"

# Expect child when config matches
COUNT_OK="$(
  curl -s "$BASE/api/v1/bom/$PARENT_ID/tree?config=$CONFIG_OK" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children", [])))'
)"
if [[ "$COUNT_OK" != "1" ]]; then
  fail "Expected 1 child for matching config, got $COUNT_OK"
fi

# Expect no child when config mismatches
COUNT_BAD="$(
  curl -s "$BASE/api/v1/bom/$PARENT_ID/tree?config=$CONFIG_BAD" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children", [])))'
)"
if [[ "$COUNT_BAD" != "0" ]]; then
  fail "Expected 0 child for mismatched config, got $COUNT_BAD"
fi

# Expect child when no config is supplied
COUNT_DEFAULT="$(
  curl -s "$BASE/api/v1/bom/$PARENT_ID/tree" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children", [])))'
)"
if [[ "$COUNT_DEFAULT" != "1" ]]; then
  fail "Expected 1 child without config filter, got $COUNT_DEFAULT"
fi

echo "ALL CHECKS PASSED"
