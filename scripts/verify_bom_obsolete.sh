#!/usr/bin/env bash
# =============================================================================
# BOM Obsolete Handling Verification Script
# =============================================================================
# Validates:
# 1) Obsolete scan detects obsolete child lines
# 2) Update mode swaps child to replacement_id
# 3) New BOM mode clones lines and updates replacements
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

# Seed identity + meta
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
  curl -s "$BASE/api/v1/aml/apply" \
    "${headers[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$number\",\"name\":\"$name\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
}

set_replacement() {
  local item_id="$1"
  local replacement_id="$2"
  curl -s "$BASE/api/v1/aml/apply" \
    "${headers[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$item_id\",\"properties\":{\"replacement_id\":\"$replacement_id\"}}" \
    >/dev/null
}

mark_obsolete() {
  local item_id="$1"
  curl -s "$BASE/api/v1/aml/apply" \
    "${headers[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$item_id\",\"properties\":{\"engineering_state\":\"obsoleted\",\"obsolete\":true}}" \
    >/dev/null
}

add_bom_child() {
  local parent_id="$1"
  local child_id="$2"
  curl -s "$BASE/api/v1/bom/$parent_id/children" \
    -X POST \
    "${headers[@]}" \
    -d "{\"child_id\":\"$child_id\",\"quantity\":1}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["relationship_id"])'
}

scan_count() {
  local parent_id="$1"
  curl -s "$BASE/api/v1/bom/$parent_id/obsolete" \
    "${headers[@]}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["count"])'
}

scan_replacement() {
  local parent_id="$1"
  curl -s "$BASE/api/v1/bom/$parent_id/obsolete" \
    "${headers[@]}" \
    | "$PY" -c 'import sys,json;data=json.load(sys.stdin);print(data["entries"][0].get("replacement_id"))'
}

resolve_mode() {
  local parent_id="$1"
  local mode="$2"
  curl -s "$BASE/api/v1/bom/$parent_id/obsolete/resolve" \
    -X POST \
    "${headers[@]}" \
    -d "{\"mode\":\"$mode\"}" \
    | "$PY" -c 'import sys,json;data=json.load(sys.stdin);print(data["summary"]["updated_lines"], data["summary"]["created_lines"])'
}

get_child_from_tree() {
  local parent_id="$1"
  curl -s "$BASE/api/v1/bom/$parent_id/tree?depth=1" \
    "${headers[@]}" \
    | "$PY" -c 'import sys,json;data=json.load(sys.stdin);print(data["children"][0]["child"]["id"])'
}

# Case 1: update mode
PARENT_1="$(create_part "OBS-PARENT-$TS" "Obsolete Parent")"
CHILD_OLD="$(create_part "OBS-OLD-$TS" "Obsolete Child")"
CHILD_NEW="$(create_part "OBS-NEW-$TS" "Replacement Child")"

mark_obsolete "$CHILD_OLD"
set_replacement "$CHILD_OLD" "$CHILD_NEW"
add_bom_child "$PARENT_1" "$CHILD_OLD" >/dev/null

count_before="$(scan_count "$PARENT_1")"
[[ "$count_before" == "1" ]] || fail "scan count before update expected 1, got $count_before"

replacement="$(scan_replacement "$PARENT_1")"
[[ "$replacement" == "$CHILD_NEW" ]] || fail "replacement id mismatch"

resolve_out="$(resolve_mode "$PARENT_1" "update")"
updated_lines="${resolve_out%% *}"
[[ "$updated_lines" == "1" ]] || fail "update mode updated_lines expected 1, got $updated_lines"

count_after="$(scan_count "$PARENT_1")"
[[ "$count_after" == "0" ]] || fail "scan count after update expected 0, got $count_after"

child_now="$(get_child_from_tree "$PARENT_1")"
[[ "$child_now" == "$CHILD_NEW" ]] || fail "child after update expected replacement"

# Case 2: new_bom mode
PARENT_2="$(create_part "OBS-PARENT2-$TS" "Obsolete Parent 2")"
CHILD_OLD2="$(create_part "OBS-OLD2-$TS" "Obsolete Child 2")"
CHILD_NEW2="$(create_part "OBS-NEW2-$TS" "Replacement Child 2")"

mark_obsolete "$CHILD_OLD2"
set_replacement "$CHILD_OLD2" "$CHILD_NEW2"
add_bom_child "$PARENT_2" "$CHILD_OLD2" >/dev/null

count_before2="$(scan_count "$PARENT_2")"
[[ "$count_before2" == "1" ]] || fail "scan count before new_bom expected 1, got $count_before2"

resolve_out2="$(resolve_mode "$PARENT_2" "new_bom")"
updated_lines2="${resolve_out2%% *}"
[[ "$updated_lines2" == "1" ]] || fail "new_bom updated_lines expected 1, got $updated_lines2"

count_after2="$(scan_count "$PARENT_2")"
[[ "$count_after2" == "0" ]] || fail "scan count after new_bom expected 0, got $count_after2"

child_now2="$(get_child_from_tree "$PARENT_2")"
[[ "$child_now2" == "$CHILD_NEW2" ]] || fail "child after new_bom expected replacement"

echo "PASS: BOM obsolete scan + resolve"
