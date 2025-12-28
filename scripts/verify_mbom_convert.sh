#!/usr/bin/env bash
# =============================================================================
# MBOM Conversion Verification Script
# Verifies: EBOM -> MBOM conversion + relationship/substitute copy
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

TENANCY_MODE="${YUANTUS_TENANCY_MODE:-${TENANCY_MODE:-single}}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

if [[ "$TENANCY_MODE" == "db-per-tenant-org" && -n "$DB_URL_TEMPLATE" ]]; then
  DB_URL="${DB_URL_TEMPLATE//\{tenant_id\}/$TENANT}"
  DB_URL="${DB_URL//\{org_id\}/$ORG}"
elif [[ "$TENANCY_MODE" == "db-per-tenant" && -n "$DB_URL_TEMPLATE" ]]; then
  DB_URL="${DB_URL_TEMPLATE//\{tenant_id\}/$TENANT}"
  DB_URL="${DB_URL//\{org_id\}/default}"
fi

if [[ -z "$DB_URL" ]]; then
  DB_URL="$(
    TENANT="$TENANT" ORG="$ORG" "$PY" - <<'PY'
import os
from yuantus.config import get_settings
from yuantus.database import resolve_database_url

tenant = os.environ.get("TENANT")
org = os.environ.get("ORG")
settings = get_settings()
try:
    url = resolve_database_url(tenant_id=tenant, org_id=org)
except Exception:
    url = settings.DATABASE_URL
print(url or "")
PY
  )"
fi

if [[ -z "$DB_URL" ]]; then
  echo "Missing DB_URL (set DB_URL=... or YUANTUS_DATABASE_URL)" >&2
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
printf "MBOM Conversion Verification\n"
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

printf "\n==> Create EBOM parts\n"
ROOT_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MBOM-R-$TS\",\"name\":\"EBOM Root\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
CHILD_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MBOM-C-$TS\",\"name\":\"EBOM Child\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
SUB_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MBOM-S-$TS\",\"name\":\"EBOM Substitute\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$ROOT_ID" || -z "$CHILD_ID" || -z "$SUB_ID" ]]; then
  fail "Failed to create EBOM parts"
fi
ok "Created EBOM root=$ROOT_ID child=$CHILD_ID substitute=$SUB_ID"

printf "\n==> Create EBOM BOM line\n"
BOM_RESP="$(
  $CURL -X POST "$API/bom/$ROOT_ID/children" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":2,\"uom\":\"EA\"}"
)"
BOM_REL_ID="$(echo "$BOM_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$BOM_REL_ID" ]]; then
  echo "Response: $BOM_RESP"
  fail "Failed to create EBOM BOM line"
fi
ok "EBOM BOM line: $BOM_REL_ID"

printf "\n==> Add substitute to EBOM BOM line\n"
SUB_RESP="$(
  $CURL -X POST "$API/bom/$BOM_REL_ID/substitutes" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"$SUB_ID\",\"properties\":{\"rank\":1}}"
)"
SUB_REL_ID="$(echo "$SUB_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("substitute_id",""))')"
if [[ -z "$SUB_REL_ID" ]]; then
  echo "Response: $SUB_RESP"
  fail "Failed to add EBOM substitute"
fi
ok "EBOM substitute relation: $SUB_REL_ID"

printf "\n==> Convert EBOM -> MBOM\n"
CONVERT_RESP="$(
  $CURL -X POST "$API/bom/convert/ebom-to-mbom" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"root_id\":\"$ROOT_ID\"}"
)"
MBOM_ROOT_ID="$(echo "$CONVERT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("mbom_root_id",""))')"
if [[ -z "$MBOM_ROOT_ID" ]]; then
  echo "Response: $CONVERT_RESP"
  fail "Failed to convert EBOM to MBOM"
fi
ok "MBOM root: $MBOM_ROOT_ID"

printf "\n==> Validate MBOM root via AML\n"
MBOM_GET="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Manufacturing Part\",\"action\":\"get\",\"id\":\"$MBOM_ROOT_ID\"}"
)"
MBOM_COUNT="$(echo "$MBOM_GET" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("count",0))')"
if [[ "$MBOM_COUNT" -ne 1 ]]; then
  echo "Response: $MBOM_GET"
  fail "Expected MBOM root to exist (count=1)"
fi
MBOM_SRC_OK="$(echo "$MBOM_GET" | "$PY" -c 'import sys,json;data=json.load(sys.stdin);props=(data.get("items") or [{}])[0].get("properties") or {};print("1" if props.get("source_ebom_id") else "0")')"
if [[ "$MBOM_SRC_OK" != "1" ]]; then
  echo "Response: $MBOM_GET"
  fail "MBOM root missing source_ebom_id"
fi
ok "MBOM root AML verified"

printf "\n==> Validate MBOM tree endpoint\n"
TREE_RESP="$($CURL "$API/bom/mbom/$MBOM_ROOT_ID/tree?depth=2" "${HEADERS[@]}" "${AUTH[@]}")"
TREE_OK="$(
  TREE_JSON="$TREE_RESP" EXPECT_CHILD="$CHILD_ID" "$PY" - <<'PY'
import json
import os

data = json.loads(os.environ.get("TREE_JSON", "{}"))
children = data.get("children") or []
if not children:
    print("0")
    raise SystemExit(0)

expected = os.environ.get("EXPECT_CHILD")
found = []
for entry in children:
    child = entry.get("child") or {}
    found.append(child.get("source_ebom_id"))

print("1" if expected in found else "0")
PY
)"
if [[ "$TREE_OK" != "1" ]]; then
  echo "Response: $TREE_RESP"
  fail "MBOM tree missing expected child"
fi
ok "MBOM tree endpoint verified"

printf "\n==> Validate MBOM structure in DB\n"
DB_URL="$DB_URL" ROOT_ID="$ROOT_ID" CHILD_ID="$CHILD_ID" SUB_ID="$SUB_ID" \
BOM_REL_ID="$BOM_REL_ID" MBOM_ROOT_ID="$MBOM_ROOT_ID" "$PY" - <<'PY'
import json
import os
from sqlalchemy import create_engine, text

db_url = os.environ["DB_URL"]
root_id = os.environ["ROOT_ID"]
child_id = os.environ["CHILD_ID"]
sub_id = os.environ["SUB_ID"]
bom_rel_id = os.environ["BOM_REL_ID"]
mbom_root_id = os.environ["MBOM_ROOT_ID"]

def parse_props(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return dict(val)

def row_get(row, key, idx):
    if hasattr(row, "_mapping"):
        return row._mapping.get(key)
    return row[idx]

engine = create_engine(db_url)
with engine.begin() as conn:
    parts = conn.execute(
        text("SELECT id, properties FROM meta_items WHERE item_type_id='Manufacturing Part'")
    ).fetchall()
    rels = conn.execute(
        text("SELECT id, source_id, related_id, properties FROM meta_items WHERE item_type_id='Manufacturing BOM'")
    ).fetchall()
    subs = conn.execute(
        text("SELECT id, source_id, related_id FROM meta_items WHERE item_type_id='Part BOM Substitute'")
    ).fetchall()

root_rows = [p for p in parts if row_get(p, "id", 0) == mbom_root_id]
if not root_rows:
    raise SystemExit("MBOM root not found in DB")
root_props = parse_props(row_get(root_rows[0], "properties", 1))
if root_props.get("source_ebom_id") != root_id:
    raise SystemExit("MBOM root source_ebom_id mismatch")

child_rows = [
    p for p in parts if parse_props(row_get(p, "properties", 1)).get("source_ebom_id") == child_id
]
if not child_rows:
    raise SystemExit("MBOM child not found for EBOM child")
sub_rows = [
    p for p in parts if parse_props(row_get(p, "properties", 1)).get("source_ebom_id") == sub_id
]
if not sub_rows:
    raise SystemExit("MBOM substitute part not found for EBOM substitute")

mbom_rel_rows = []
for r in rels:
    if row_get(r, "source_id", 1) != mbom_root_id:
        continue
    props = parse_props(row_get(r, "properties", 3))
    if props.get("source_rel_id") == bom_rel_id:
        mbom_rel_rows.append(r)
if not mbom_rel_rows:
    raise SystemExit("MBOM BOM relationship not found")

mbom_rel_id = row_get(mbom_rel_rows[0], "id", 0)
sub_rel_rows = [s for s in subs if row_get(s, "source_id", 1) == mbom_rel_id]
if not sub_rel_rows:
    raise SystemExit("MBOM substitute relationship not found")

mbom_sub_id = row_get(sub_rows[0], "id", 0)
if row_get(sub_rel_rows[0], "related_id", 2) != mbom_sub_id:
    raise SystemExit("MBOM substitute relation does not reference converted part")

print("MBOM structure: OK")
PY
ok "MBOM structure verified"

printf "\n==============================================\n"
printf "MBOM Conversion Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
