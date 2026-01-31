#!/usr/bin/env bash
# =============================================================================
# P3 MBOM + Routing Verification
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

"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null

TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"

PARENT_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MBOM-P-$TS\",\"name\":\"MBOM Parent\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MBOM-C-$TS\",\"name\":\"MBOM Child\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

curl -s -X POST "$BASE/api/v1/bom/$PARENT_ID/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":2,\"uom\":\"EA\"}" >/dev/null

MBOM_ID="$(
  curl -s -X POST "$BASE/api/v1/mboms/from-ebom" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"source_item_id\":\"$PARENT_ID\",\"name\":\"MBOM-$TS\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

if [[ -z "$MBOM_ID" ]]; then
  fail "MBOM create failed"
fi

CHILD_COUNT="$(
  curl -s "$BASE/api/v1/mboms/$MBOM_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;print(len((json.load(sys.stdin).get("children") or [])))'
)"

if [[ "$CHILD_COUNT" != "1" ]]; then
  fail "Expected MBOM children=1, got $CHILD_COUNT"
fi

ROUTING_ID="$(
  curl -s -X POST "$BASE/api/v1/routings" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"name\":\"Routing-$TS\",\"mbom_id\":\"$MBOM_ID\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"

curl -s -X POST "$BASE/api/v1/routings/$ROUTING_ID/operations" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"operation_number":"10","name":"Cut","setup_time":5,"run_time":1}' >/dev/null

curl -s -X POST "$BASE/api/v1/routings/$ROUTING_ID/operations" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"operation_number":"20","name":"Assemble","setup_time":10,"run_time":2}' >/dev/null

TOTAL_TIME="$(
  curl -s -X POST "$BASE/api/v1/routings/$ROUTING_ID/calculate-time" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d '{"quantity":5}' \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["total_time"])'
)"

if ! "$PY" - "$TOTAL_TIME" >/dev/null 2>&1 <<'PY'
import sys
float(sys.argv[1])
PY
then
  fail "Invalid total_time: $TOTAL_TIME"
fi

TOTAL_COST="$(
  curl -s -X POST "$BASE/api/v1/routings/$ROUTING_ID/calculate-cost" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d '{"quantity":5}' \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["total_cost"])'
)"

if ! "$PY" - "$TOTAL_COST" >/dev/null 2>&1 <<'PY'
import sys
float(sys.argv[1])
PY
then
  fail "Invalid total_cost: $TOTAL_COST"
fi

echo "PASS: MBOM + routing + time/cost"
