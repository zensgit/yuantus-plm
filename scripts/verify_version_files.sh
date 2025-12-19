#!/usr/bin/env bash
# =============================================================================
# Version-File Binding Verification Script
# Verifies: file lock on checkout + checkin syncs files to VersionFile
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
printf "Version-File Binding Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 100000))}"
VIEWER_UID="${VIEWER_UID:-$((ADMIN_UID + 1))}"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id "$ADMIN_UID" --roles admin >/dev/null
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username viewer --password viewer --user-id "$VIEWER_UID" --roles viewer >/dev/null
"$CLI" seed-meta >/dev/null
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

printf "\n==> Login as viewer\n"
VIEWER_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"viewer\",\"password\":\"viewer\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$VIEWER_TOKEN" ]]; then
  fail "Viewer login failed (no access_token)"
fi
VIEWER_AUTH=(-H "Authorization: Bearer $VIEWER_TOKEN")
ok "Viewer login"

TS="$(date +%s)"

printf "\n==> Create Part item\n"
ITEM_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"VF-$TS\",\"name\":\"Version File Bind\"}}" \
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
TEST_FILE="$TMP_DIR/vf_test.txt"
echo "version-file-bind $TS" > "$TEST_FILE"
UPLOAD_RESP="$(
  $CURL -X POST "$API/file/upload" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -F "file=@$TEST_FILE;filename=version_file_$TS.txt"
)"
FILE_ID="$(echo "$UPLOAD_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$FILE_ID" ]]; then
  echo "Response: $UPLOAD_RESP"
  fail "File upload failed"
fi
ok "Uploaded file: $FILE_ID"

printf "\n==> Attach file to item (native_cad)\n"
ATTACH_RESP="$(
  $CURL -X POST "$API/file/attach" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"item_id\":\"$ITEM_ID\",\"file_id\":\"$FILE_ID\",\"file_role\":\"native_cad\"}"
)"
ATTACH_STATUS="$(echo "$ATTACH_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status",""))')"
if [[ -z "$ATTACH_STATUS" ]]; then
  echo "Response: $ATTACH_RESP"
  fail "Attach file failed"
fi
ok "File attached to item"

printf "\n==> Checkout version (lock files)\n"
CHECKOUT_RESP="$(
  $CURL -X POST "$API/versions/items/$ITEM_ID/checkout" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d '{"comment":"lock files"}'
)"
CHECKOUT_ID="$(echo "$CHECKOUT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$CHECKOUT_ID" ]]; then
  echo "Response: $CHECKOUT_RESP"
  fail "Checkout failed"
fi
ok "Checked out version"

printf "\n==> Viewer attach should be blocked (409)\n"
DUP_FILE="$TMP_DIR/attach_viewer.json"
HTTP_CODE="$(curl -s -o "$DUP_FILE" -w '%{http_code}' \
  -X POST "$API/file/attach" "${HEADERS[@]}" "${VIEWER_AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"item_id\":\"$ITEM_ID\",\"file_id\":\"$FILE_ID\",\"file_role\":\"attachment\"}")"
if [[ "$HTTP_CODE" != "409" ]]; then
  echo "Response: $(cat "$DUP_FILE")"
  fail "Expected 409 when attaching during checkout, got $HTTP_CODE"
fi
ok "Attach blocked for non-owner"

printf "\n==> Checkin version (sync files)\n"
CHECKIN_RESP="$(
  $CURL -X POST "$API/versions/items/$ITEM_ID/checkin" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d '{"comment":"sync files"}'
)"
CHECKIN_ID="$(echo "$CHECKIN_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$CHECKIN_ID" ]]; then
  echo "Response: $CHECKIN_RESP"
  fail "Checkin failed"
fi
ok "Checked in version"

printf "\n==> Verify version files\n"
FILES_RESP="$(
  $CURL "$API/versions/$VERSION_ID/files" "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"
FILES_JSON="$FILES_RESP" FILE_ID="$FILE_ID" $PY - <<'PY'
import os
import json

data = json.loads(os.environ["FILES_JSON"])
file_id = os.environ["FILE_ID"]
roles = [f.get("file_role") for f in data if f.get("file_id") == file_id]
assert "native_cad" in roles, f"expected native_cad for {file_id}, got {roles}"
print("Version files synced: OK")
PY

printf "\n==============================================\n"
printf "Version-File Binding Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
