#!/usr/bin/env bash
# =============================================================================
# S2 Documents & Files Verification Script
# =============================================================================
# Validates:
# 1. File metadata (author/source/version)
# 2. Checksum-based dedupe
# 3. Item attachments list
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

TS="$(date +%s)"
TMP_FILE="/tmp/yuantus_doc_${TS}.txt"
echo "Yuantus Documents Test ${TS}" > "$TMP_FILE"

echo "=============================================="
echo "Documents & Files Verification"
echo "BASE_URL: $BASE"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null
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
  echo "FAIL: Admin login failed" >&2
  exit 1
fi
echo "OK: Admin login"

echo ""
echo "==> Create Part"
PART_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"DOC-${TS}\",\"name\":\"Document Test Part\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "OK: Created Part: $PART_ID"

echo ""
echo "==> Upload file with metadata"
UPLOAD_JSON="$(
  curl -s -X POST "$BASE/api/v1/file/upload?generate_preview=false" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -F "file=@${TMP_FILE}" \
    -F "author=Doc Author" \
    -F "source_system=legacy-plm" \
    -F "source_version=v1" \
    -F "document_version=A.1"
)"
FILE_ID="$(echo "$UPLOAD_JSON" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
echo "OK: Uploaded file: $FILE_ID"

echo ""
echo "==> Verify file metadata"
curl -s "$BASE/api/v1/file/${FILE_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d["author"]=="Doc Author";assert d["source_system"]=="legacy-plm";assert d["source_version"]=="v1";assert d["document_version"]=="A.1";print("OK: Metadata verified")'

echo ""
echo "==> Upload duplicate file (checksum dedupe)"
DUP_JSON="$(
  curl -s -X POST "$BASE/api/v1/file/upload?generate_preview=false" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -F "file=@${TMP_FILE}"
)"
DUP_ID="$(echo "$DUP_JSON" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
if [[ "$DUP_ID" != "$FILE_ID" ]]; then
  echo "FAIL: Dedupe returned different id ($DUP_ID != $FILE_ID)" >&2
  exit 1
fi
echo "OK: Dedupe returned same file id"

echo ""
echo "==> Attach file to item"
curl -s -X POST "$BASE/api/v1/file/attach" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"item_id\":\"$PART_ID\",\"file_id\":\"$FILE_ID\",\"file_role\":\"attachment\",\"description\":\"doc attachment\"}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("status") in ("created","updated");print("OK: Attachment created")'

echo ""
echo "==> Verify item attachment list"
curl -s "$BASE/api/v1/file/item/${PART_ID}?role=attachment" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;items=json.load(sys.stdin);match=[i for i in items if i.get("file_id")==sys.argv[1]];assert match;entry=match[0];assert entry.get("author")=="Doc Author";assert entry.get("source_system")=="legacy-plm";assert entry.get("source_version")=="v1";assert entry.get("document_version")=="A.1";print("OK: Attachment list verified")' \
    "$FILE_ID"

echo ""
echo "==> Cleanup"
rm -f "$TMP_FILE"
echo "OK: Cleaned up temp file"

echo ""
echo "=============================================="
echo "Documents & Files Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
