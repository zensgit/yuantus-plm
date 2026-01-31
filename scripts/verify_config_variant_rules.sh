#!/usr/bin/env bash
# =============================================================================
# P2 Variant Rule Verification
# =============================================================================
set -euo pipefail

BASE="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-python3}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Missing python at $PY (set PY=...)" >&2
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
TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"

# Create option set + options
MODE_SET_ID="$(
  curl -s -X POST "$BASE/api/v1/config/option-sets" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"name\":\"Mode-$TS\",\"label\":\"Mode\",\"value_type\":\"string\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

curl -s -X POST "$BASE/api/v1/config/option-sets/$MODE_SET_ID/options" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"key":"Standard","value":"Standard"}' >/dev/null

curl -s -X POST "$BASE/api/v1/config/option-sets/$MODE_SET_ID/options" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"key":"Premium","value":"Premium"}' >/dev/null

# Create parent/child parts
PARENT_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-P2-$TS\",\"name\":\"Config P2 Parent\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"CFG-P2-C-$TS\",\"name\":\"Config P2 Child\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":1,\"uom\":\"EA\"}" >/dev/null

# Create variant rule: exclude child when Mode=Standard
RULE_ID="$(
  curl -s -X POST "$BASE/api/v1/config/variant-rules" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"name\":\"P2 Exclude Standard\",\"parent_item_id\":\"$PARENT_ID\",\"condition\":{\"option\":\"Mode-$TS\",\"value\":\"Standard\"},\"action_type\":\"exclude\",\"target_item_id\":\"$CHILD_ID\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

if [[ -z "$RULE_ID" ]]; then
  fail "Variant rule create failed"
fi

COUNT_STANDARD="$(
  curl -s -X POST "$BASE/api/v1/config/effective-bom" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"product_item_id\":\"$PARENT_ID\",\"selections\":{\"Mode-$TS\":\"Standard\"},\"levels\":2}" \
    | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children") or []))'
)"

COUNT_PREMIUM="$(
  curl -s -X POST "$BASE/api/v1/config/effective-bom" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"product_item_id\":\"$PARENT_ID\",\"selections\":{\"Mode-$TS\":\"Premium\"},\"levels\":2}" \
    | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("children") or []))'
)"

if [[ "$COUNT_STANDARD" != "0" ]]; then
  fail "Expected 0 children for Standard, got $COUNT_STANDARD"
fi
if [[ "$COUNT_PREMIUM" != "1" ]]; then
  fail "Expected 1 child for Premium, got $COUNT_PREMIUM"
fi

CONFIG_CHILDREN="$(
  curl -s -X POST "$BASE/api/v1/config/configurations" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"product_item_id\":\"$PARENT_ID\",\"name\":\"Config Premium\",\"selections\":{\"Mode-$TS\":\"Premium\"}}" \
    | "$PY" -c 'import sys,json;data=json.load(sys.stdin);print(len((data.get("effective_bom_cache") or {}).get("children") or []))'
)"

if [[ "$CONFIG_CHILDREN" != "1" ]]; then
  fail "Expected configuration cache children=1, got $CONFIG_CHILDREN"
fi

echo "PASS: variant rules + effective BOM + configuration cache"
