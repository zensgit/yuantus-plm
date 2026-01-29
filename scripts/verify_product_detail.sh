#!/usr/bin/env bash
# =============================================================================
# Product Detail Mapping Verification
# Verifies: item + current_version + versions + files aggregation
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

fail() { echo "FAIL: $1"; exit 1; }
ok() { echo "OK: $1"; }

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

printf "==============================================\n"
printf "Product Detail Mapping Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 100000))}"
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
ITEM_NUMBER="PD-$TS"

printf "\n==> Create Part item\n"
ITEM_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$ITEM_NUMBER\",\"name\":\"Product Detail $TS\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$ITEM_ID" ]]; then
  fail "Failed to create Part"
fi
ok "Created Part: $ITEM_ID"

printf "\n==> Init version\n"
VER_RESP="$(
  $CURL -X POST "$API/versions/items/$ITEM_ID/init" "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"
VERSION_ID="$(echo "$VER_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$VERSION_ID" ]]; then
  echo "Response: $VER_RESP"
  fail "Failed to init version"
fi
ok "Init version: $VERSION_ID"

printf "\n==> Upload file\n"
TEST_FILE="$TMP_DIR/product_detail.txt"
echo "product-detail $TS" > "$TEST_FILE"
UPLOAD_RESP="$(
  $CURL -X POST "$API/file/upload" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -F "file=@$TEST_FILE;filename=product_detail_$TS.txt"
)"
FILE_ID="$(echo "$UPLOAD_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$FILE_ID" ]]; then
  echo "Response: $UPLOAD_RESP"
  fail "File upload failed"
fi
ok "Uploaded file: $FILE_ID"

printf "\n==> Attach file to item\n"
ATTACH_RESP="$(
  $CURL -X POST "$API/file/attach" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"item_id\":\"$ITEM_ID\",\"file_id\":\"$FILE_ID\",\"file_role\":\"attachment\"}"
)"
ATTACH_STATUS="$(echo "$ATTACH_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status",""))')"
if [[ -z "$ATTACH_STATUS" ]]; then
  echo "Response: $ATTACH_RESP"
  fail "Attach file failed"
fi
ok "File attached to item"

printf "\n==> Fetch product detail\n"
DETAIL_RESP="$(
  $CURL "$API/products/$ITEM_ID?include_versions=true&include_files=true" \
    "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

DETAIL_JSON="$DETAIL_RESP" ITEM_ID="$ITEM_ID" FILE_ID="$FILE_ID" ITEM_NUMBER="$ITEM_NUMBER" "$PY" - <<'PY'
import os
import json

data = json.loads(os.environ["DETAIL_JSON"])
item = data.get("item") or {}
props = item.get("properties") or {}

expected_id = os.environ["ITEM_ID"]
expected_number = os.environ["ITEM_NUMBER"]
file_id = os.environ["FILE_ID"]

if item.get("id") != expected_id:
    raise SystemExit(f"item id mismatch: {item.get('id')} != {expected_id}")

number = item.get("item_number") or props.get("item_number") or item.get("number") or props.get("number")
if number != expected_number:
    raise SystemExit(f"item_number mismatch: {number} != {expected_number}")

item_type = item.get("item_type_id") or item.get("item_type") or item.get("type")
if item_type != "Part":
    raise SystemExit(f"item_type mismatch: {item_type} != Part")

if item.get("status") != item.get("state"):
    raise SystemExit("status should mirror state")

if not item.get("created_on"):
    raise SystemExit("missing created_on")
if not item.get("modified_on"):
    raise SystemExit("missing modified_on")

current_version = data.get("current_version") or {}
if not current_version.get("id"):
    raise SystemExit("missing current_version")

versions = data.get("versions") or []
if not versions:
    raise SystemExit("missing versions")

files = data.get("files") or []
if not any(f.get("file_id") == file_id for f in files):
    raise SystemExit(f"file {file_id} not found in files")

print("Product detail mapping: OK")
PY

printf "\n==============================================\n"
printf "Product Detail Mapping Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
