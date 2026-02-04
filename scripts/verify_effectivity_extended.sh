#!/usr/bin/env bash
# =============================================================================
# Effectivity (Lot/Serial) Verification Script
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

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

echo "=============================================="
echo "Effectivity Extended Verification"
echo "BASE_URL: $BASE"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || "$CLI" seed-meta >/dev/null
echo "OK: Seeded identity/meta"

echo ""
echo "==> Login as admin"
TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"
if [[ -z "$TOKEN" ]]; then
  fail "Admin login failed"
fi
echo "OK: Admin login"

TS="$(date +%s)"
echo ""
echo "==> Create Parts"
PARENT_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EFF-${TS}-P\",\"name\":\"Eff Parent\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD_LOT_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EFF-${TS}-L\",\"name\":\"Eff Lot\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
CHILD_SERIAL_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EFF-${TS}-S\",\"name\":\"Eff Serial\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
if [[ -z "$PARENT_ID" || -z "$CHILD_LOT_ID" || -z "$CHILD_SERIAL_ID" ]]; then
  fail "Part creation failed"
fi
echo "OK: Created Parts"

echo ""
echo "==> Add BOM relationships"
REL_LOT_ID="$(
  curl -s -X POST "$BASE/api/v1/bom/${PARENT_ID}/children" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$CHILD_LOT_ID\",\"quantity\":1}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["relationship_id"])'
)"
REL_SERIAL_ID="$(
  curl -s -X POST "$BASE/api/v1/bom/${PARENT_ID}/children" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"child_id\":\"$CHILD_SERIAL_ID\",\"quantity\":1}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["relationship_id"])'
)"
if [[ -z "$REL_LOT_ID" || -z "$REL_SERIAL_ID" ]]; then
  fail "BOM add failed"
fi
echo "OK: BOM relationships created"

echo ""
echo "==> Create Lot effectivity"
LOT_EFF_ID="$(
  curl -s -X POST "$BASE/api/v1/effectivities" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"item_id\":\"$REL_LOT_ID\",\"effectivity_type\":\"Lot\",\"payload\":{\"lot_start\":\"L010\",\"lot_end\":\"L020\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$LOT_EFF_ID" ]]; then
  fail "Lot effectivity create failed"
fi
echo "OK: Lot effectivity created"

echo ""
echo "==> Create Serial effectivity"
SERIAL_EFF_ID="$(
  curl -s -X POST "$BASE/api/v1/effectivities" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"item_id\":\"$REL_SERIAL_ID\",\"effectivity_type\":\"Serial\",\"payload\":{\"serials\":[\"SN-1\",\"SN-2\"]}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$SERIAL_EFF_ID" ]]; then
  fail "Serial effectivity create failed"
fi
echo "OK: Serial effectivity created"

echo ""
echo "==> Query effective BOM with matching lot/serial"
RESP="$(
  curl -s "$BASE/api/v1/bom/${PARENT_ID}/effective?lot_number=L015&serial_number=SN-1&levels=1" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
COUNT="$(
  printf '%s' "$RESP" | "$PY" -c 'import sys,json;data=json.load(sys.stdin);print(len(data.get("children",[])))'
)"
if [[ "$COUNT" != "2" ]]; then
  echo "$RESP" >&2
  fail "Expected 2 children for matching lot/serial, got $COUNT"
fi
echo "OK: Both children visible"

echo ""
echo "==> Query effective BOM with non-matching lot/serial"
RESP="$(
  curl -s "$BASE/api/v1/bom/${PARENT_ID}/effective?lot_number=L030&serial_number=SN-9&levels=1" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
COUNT="$(
  printf '%s' "$RESP" | "$PY" -c 'import sys,json;data=json.load(sys.stdin);print(len(data.get("children",[])))'
)"
if [[ "$COUNT" != "0" ]]; then
  echo "$RESP" >&2
  fail "Expected 0 children for non-matching lot/serial, got $COUNT"
fi
echo "OK: Children filtered out"

echo "=============================================="
echo "Effectivity Extended Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
