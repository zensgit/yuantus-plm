#!/usr/bin/env bash
# =============================================================================
# Where-Used UI Verification
# Validates line fields + recursive metadata in where-used responses.
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

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

printf "==============================================\n"
printf "Where-Used UI Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 500000))}"
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
GRAND_NUM="WU-G-$TS"
PARENT_NUM="WU-P-$TS"
CHILD_NUM="WU-C-$TS"

create_part() {
  local num="$1"
  local name="$2"
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$num\",\"name\":\"$name\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
}

printf "\n==> Create Parts\n"
GRAND_ID="$(create_part "$GRAND_NUM" "WU Grand $TS")"
PARENT_ID="$(create_part "$PARENT_NUM" "WU Parent $TS")"
CHILD_ID="$(create_part "$CHILD_NUM" "WU Child $TS")"

if [[ -z "$GRAND_ID" || -z "$PARENT_ID" || -z "$CHILD_ID" ]]; then
  fail "Failed to create where-used parts"
fi
ok "Created Parts: grand=$GRAND_ID parent=$PARENT_ID child=$CHILD_ID"

printf "\n==> Add BOM lines\n"
REL_PARENT="$(
  $CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"10\"}"
)"
REL_PARENT_ID="$(echo "$REL_PARENT" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_PARENT_ID" ]]; then
  echo "Response: $REL_PARENT"
  fail "Failed to add parent->child"
fi

REL_GRAND="$(
  $CURL -X POST "$API/bom/$GRAND_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$PARENT_ID\",\"quantity\":1,\"uom\":\"EA\",\"find_num\":\"20\"}"
)"
REL_GRAND_ID="$(echo "$REL_GRAND" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_GRAND_ID" ]]; then
  echo "Response: $REL_GRAND"
  fail "Failed to add grand->parent"
fi
ok "Added BOM lines: parent_rel=$REL_PARENT_ID grand_rel=$REL_GRAND_ID"

printf "\n==> Where-used (recursive)\n"
WHERE_USED_RESP="$(
  $CURL "$API/bom/$CHILD_ID/where-used?recursive=true&max_levels=3" "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

WHERE_USED_JSON="$WHERE_USED_RESP" CHILD_ID="$CHILD_ID" PARENT_ID="$PARENT_ID" GRAND_ID="$GRAND_ID" "$PY" - <<'PY'
import os
import json

data = json.loads(os.environ["WHERE_USED_JSON"])
parent_id = os.environ["PARENT_ID"]
grand_id = os.environ["GRAND_ID"]

if data.get("recursive") is not True:
    raise SystemExit("recursive flag missing or false")
if data.get("max_levels") != 3:
    raise SystemExit("max_levels mismatch")

parents = data.get("parents") or []
if len(parents) < 2:
    raise SystemExit("expected at least 2 where-used entries")

parent_ids = {p.get("parent", {}).get("id") for p in parents}
if parent_id not in parent_ids or grand_id not in parent_ids:
    raise SystemExit("missing expected parent/grand entries")

for entry in parents:
    line = entry.get("line") or {}
    line_norm = entry.get("line_normalized") or {}
    if "quantity" not in line or "quantity" not in line_norm:
        raise SystemExit("missing line quantity fields")
    child = entry.get("child") or {}
    rel = entry.get("relationship") or {}
    if child.get("id") != rel.get("related_id"):
        raise SystemExit("child mismatch in where-used entry")

print("Where-used UI payload: OK")
PY

printf "\n==============================================\n"
printf "Where-Used UI Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
