#!/usr/bin/env bash
# =============================================================================
# CADGF preview online verification (E2E).
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-}"
TENANT="${TENANT:-tenant-1}"
ORG="${ORG:-org-1}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
SAMPLE_FILE="${SAMPLE_FILE:-}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
REPORT_PATH="${REPORT_PATH:-/tmp/cadgf_preview_online_report.md}"

if [[ -z "$BASE_URL" ]]; then
  echo "Missing BASE_URL (e.g. https://plm.example.com)" >&2
  exit 2
fi
if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "Missing SAMPLE_FILE (DXF recommended)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "Missing python3 (set PY=...)" >&2
    exit 2
  fi
fi

AUTH_HEADER=()
if [[ -n "$AUTH_TOKEN" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $AUTH_TOKEN")
else
  LOGIN_RESP="$($CURL -X POST "$BASE_URL/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\",\"org_id\":\"$ORG\"}")"
  AUTH_TOKEN="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))' <<<"$LOGIN_RESP")"
  if [[ -z "$AUTH_TOKEN" ]]; then
    echo "Login failed (no access_token). Provide AUTH_TOKEN or credentials." >&2
    exit 2
  fi
  AUTH_HEADER=(-H "Authorization: Bearer $AUTH_TOKEN")
fi

HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

FILE_RESP="$($CURL -X POST "$BASE_URL/api/v1/file/upload" \
  "${HEADERS[@]}" "${AUTH_HEADER[@]}" \
  -F "file=@$SAMPLE_FILE")"
FILE_ID="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("id",""))' <<<"$FILE_RESP")"
if [[ -z "$FILE_ID" ]]; then
  echo "Upload failed: $FILE_RESP" >&2
  exit 1
fi

META_RESP="$($CURL "$BASE_URL/api/v1/file/$FILE_ID" "${HEADERS[@]}" "${AUTH_HEADER[@]}")"
CAD_VIEWER_URL="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("cad_viewer_url",""))' <<<"$META_RESP")"
CAD_MANIFEST_URL="$BASE_URL/api/v1/file/$FILE_ID/cad_manifest?rewrite=1"

VIEWER_OK="no"
if [[ -n "$CAD_VIEWER_URL" ]]; then
  if $CURL "$CAD_VIEWER_URL" | grep -q "Web Preview"; then
    VIEWER_OK="yes"
  fi
fi

MANIFEST_OK="no"
MANIFEST_ARTIFACTS="$($CURL "$CAD_MANIFEST_URL" "${HEADERS[@]}" "${AUTH_HEADER[@]}" | "$PY" - <<'PY'
import json,sys
data = json.load(sys.stdin)
art = data.get("artifacts", {})
print(json.dumps(art, indent=2, sort_keys=True))
PY
)"
if echo "$MANIFEST_ARTIFACTS" | grep -q "http"; then
  MANIFEST_OK="yes"
fi

cat >"$REPORT_PATH" <<EOF
# CADGF Preview Online Verification Report

## Inputs
- BASE_URL: $BASE_URL
- TENANT/ORG: $TENANT / $ORG
- SAMPLE_FILE: $SAMPLE_FILE

## Results
- file_id: $FILE_ID
- cad_viewer_url: $CAD_VIEWER_URL
- viewer_load: $VIEWER_OK
- manifest_rewrite: $MANIFEST_OK

## Manifest Artifacts (rewrite=1)
\`\`\`json
$MANIFEST_ARTIFACTS
\`\`\`
EOF

echo "report: $REPORT_PATH"
