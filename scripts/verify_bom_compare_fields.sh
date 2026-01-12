#!/usr/bin/env bash
# =============================================================================
# BOM Compare Field Contract Verification
# Verifies normalized line fields are included for compare output.
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
printf "BOM Compare Field Contract Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 300000))}"
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
LEFT_NUM="CMP-L-$TS"
RIGHT_NUM="CMP-R-$TS"
CHILD_NUM="CMP-C-$TS"
SUB_NUM="CMP-S-$TS"

create_part() {
  local num="$1"
  local name="$2"
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$num\",\"name\":\"$name\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
}

printf "\n==> Create Parts\n"
LEFT_ID="$(create_part "$LEFT_NUM" "Compare Left $TS")"
RIGHT_ID="$(create_part "$RIGHT_NUM" "Compare Right $TS")"
CHILD_ID="$(create_part "$CHILD_NUM" "Compare Child $TS")"
SUB_ID="$(create_part "$SUB_NUM" "Compare Substitute $TS")"

if [[ -z "$LEFT_ID" || -z "$RIGHT_ID" || -z "$CHILD_ID" || -z "$SUB_ID" ]]; then
  fail "Failed to create compare parts"
fi
ok "Created Parts: left=$LEFT_ID right=$RIGHT_ID child=$CHILD_ID sub=$SUB_ID"

EFF_FROM="$($PY - <<'PY'
from datetime import datetime, timedelta
print((datetime.utcnow() - timedelta(days=1)).isoformat())
PY
)"
EFF_TO="$($PY - <<'PY'
from datetime import datetime, timedelta
print((datetime.utcnow() + timedelta(days=1)).isoformat())
PY
)"
EFF_FROM_2="$($PY - <<'PY'
from datetime import datetime, timedelta
print((datetime.utcnow() + timedelta(days=2)).isoformat())
PY
)"
EFF_TO_2="$($PY - <<'PY'
from datetime import datetime, timedelta
print((datetime.utcnow() + timedelta(days=4)).isoformat())
PY
)"

printf "\n==> Add BOM lines\n"
REL_LEFT_RESP="$(
  $CURL -X POST "$API/bom/$LEFT_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":1,\"uom\":\"EA\",\"find_num\":\"10\",\"refdes\":\"R1 R2\",\"effectivity_from\":\"$EFF_FROM\",\"effectivity_to\":\"$EFF_TO\"}"
)"
REL_LEFT_ID="$(echo "$REL_LEFT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_LEFT_ID" ]]; then
  echo "Response: $REL_LEFT_RESP"
  fail "Failed to add left BOM line"
fi

REL_RIGHT_RESP="$(
  $CURL -X POST "$API/bom/$RIGHT_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"20\",\"refdes\":\"R3\",\"effectivity_from\":\"$EFF_FROM_2\",\"effectivity_to\":\"$EFF_TO_2\"}"
)"
REL_RIGHT_ID="$(echo "$REL_RIGHT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_RIGHT_ID" ]]; then
  echo "Response: $REL_RIGHT_RESP"
  fail "Failed to add right BOM line"
fi
ok "Added BOM lines: left_rel=$REL_LEFT_ID right_rel=$REL_RIGHT_ID"

printf "\n==> Add substitute to left BOM line\n"
SUB_RESP="$(
  $CURL -X POST "$API/bom/$REL_LEFT_ID/substitutes" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"$SUB_ID\",\"properties\":{\"rank\":1}}"
)"
SUB_REL_ID="$(echo "$SUB_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("substitute_id",""))')"
if [[ -z "$SUB_REL_ID" ]]; then
  echo "Response: $SUB_RESP"
  fail "Failed to add substitute"
fi
ok "Added substitute: $SUB_REL_ID"

printf "\n==> Compare BOMs\n"
COMPARE_RESP="$(
  $CURL "$API/bom/compare?left_type=item&left_id=$LEFT_ID&right_type=item&right_id=$RIGHT_ID&max_levels=5&include_child_fields=true&include_substitutes=true&include_effectivity=true" \
    "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

COMPARE_JSON="$COMPARE_RESP" "$PY" - <<'PY'
import os
import json

data = json.loads(os.environ["COMPARE_JSON"])
changed = data.get("changed") or []
if not changed:
    raise SystemExit("compare returned no changed entries")

entry = changed[0]
for key in ("before_line", "after_line", "before_normalized", "after_normalized"):
    if key not in entry:
        raise SystemExit(f"missing {key}")

line = entry["before_line"] or {}
line_norm = entry["before_normalized"] or {}
required_fields = [
    "quantity",
    "uom",
    "find_num",
    "refdes",
    "effectivity_from",
    "effectivity_to",
    "effectivities",
    "substitutes",
]
for field in required_fields:
    if field not in line:
        raise SystemExit(f"missing line field: {field}")
    if field not in line_norm:
        raise SystemExit(f"missing normalized field: {field}")

subs = line.get("substitutes") or []
effs = line.get("effectivities") or []
if not subs:
    raise SystemExit("expected substitutes on left line")
if not effs:
    raise SystemExit("expected effectivities on left line")

changes = entry.get("changes") or []
changed_fields = {c.get("field") for c in changes}
if "quantity" not in changed_fields or "find_num" not in changed_fields:
    raise SystemExit(f"missing expected change fields: {changed_fields}")

print("BOM compare field contract: OK")
PY

printf "\n==============================================\n"
printf "BOM Compare Field Contract Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
