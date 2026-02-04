#!/usr/bin/env bash
# =============================================================================
# BOM Weight Rollup Verification Script
# =============================================================================
# Validates:
# 1) Rollup totals match sum(child_weight * qty)
# 2) write_back updates parent weight when missing
# =============================================================================
set -euo pipefail

BASE="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
MODE="${MODE:-}"
DB_URL="${DB_URL:-}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$MODE" || -n "$DB_URL" || -n "$DB_URL_TEMPLATE" || -n "$identity_url" ]]; then
    env \
      ${MODE:+YUANTUS_TENANCY_MODE="$MODE"} \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL="$DB_URL_TEMPLATE"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

TS="$(date +%s)"

run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null

ADMIN_TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"

headers=(
  -H "Authorization: Bearer $ADMIN_TOKEN"
  -H "x-tenant-id: $TENANT"
  -H "x-org-id: $ORG"
  -H 'content-type: application/json'
)

create_part() {
  local number="$1"
  local name="$2"
  local weight="$3"
  curl -s "$BASE/api/v1/aml/apply" \
    "${headers[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$number\",\"name\":\"$name\",\"weight\":$weight}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
}

create_part_no_weight() {
  local number="$1"
  local name="$2"
  curl -s "$BASE/api/v1/aml/apply" \
    "${headers[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$number\",\"name\":\"$name\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
}

add_bom_child() {
  local parent_id="$1"
  local child_id="$2"
  local qty="$3"
  curl -s "$BASE/api/v1/bom/$parent_id/children" \
    -X POST \
    "${headers[@]}" \
    -d "{\"child_id\":\"$child_id\",\"quantity\":$qty}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["relationship_id"])' >/dev/null
}

get_weight_prop() {
  local item_id="$1"
  curl -s "$BASE/api/v1/aml/apply" \
    "${headers[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"get\",\"id\":\"$item_id\"}" \
    | "$PY" -c 'import sys,json;data=json.load(sys.stdin);print(data.get("items",[])[0].get("properties",{}).get("weight_rollup"))'
}

PARENT="$(create_part_no_weight "ROLLUP-P-$TS" "Rollup Parent")"
CHILD1="$(create_part "ROLLUP-C1-$TS" "Child 1" 2.5)"
CHILD2="$(create_part "ROLLUP-C2-$TS" "Child 2" 1.0)"

add_bom_child "$PARENT" "$CHILD1" 2
add_bom_child "$PARENT" "$CHILD2" 3

ROLLUP_JSON="$(
  curl -s "$BASE/api/v1/bom/$PARENT/rollup/weight" \
    -X POST \
    "${headers[@]}" \
    -d '{"write_back":true,"write_back_field":"weight_rollup","write_back_mode":"missing","rounding":3}'
)"

TOTAL_WEIGHT="$(
  echo "$ROLLUP_JSON" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["summary"]["total_weight"])'
)"

EXPECTED="8.0"
MATCH="$(
  "$PY" - <<PY
import math
try:
    total=float("$TOTAL_WEIGHT")
    expected=float("$EXPECTED")
    print('1' if math.isclose(total, expected, rel_tol=1e-6, abs_tol=1e-6) else '0')
except Exception:
    print('0')
PY
)"

[[ "$MATCH" == "1" ]] || fail "rollup total expected $EXPECTED, got $TOTAL_WEIGHT"

PARENT_WEIGHT="$(get_weight_prop "$PARENT")"
MATCH2="$(
  "$PY" - <<PY
import math
try:
    total=float("$PARENT_WEIGHT")
    expected=float("$EXPECTED")
    print('1' if math.isclose(total, expected, rel_tol=1e-6, abs_tol=1e-6) else '0')
except Exception:
    print('0')
PY
)"

[[ "$MATCH2" == "1" ]] || fail "write_back weight expected $EXPECTED, got $PARENT_WEIGHT"

echo "PASS: BOM weight rollup"
