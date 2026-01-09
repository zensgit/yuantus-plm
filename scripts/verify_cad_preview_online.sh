#!/usr/bin/env bash
# =============================================================================
# CADGF preview online verification (E2E).
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-}"
TENANT="${TENANT:-tenant-1}"
ORG="${ORG:-org-1}"
LOGIN_USERNAME="${LOGIN_USERNAME:-${USERNAME:-admin}}"
PASSWORD="${PASSWORD:-admin}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
SAMPLE_FILE="${SAMPLE_FILE:-}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
REPORT_PATH="${REPORT_PATH:-/tmp/cadgf_preview_online_report.md}"
SYNC_GEOMETRY="${SYNC_GEOMETRY:-${CADGF_SYNC_GEOMETRY:-0}}"

LOGIN_OK="no"
UPLOAD_OK="no"
CONVERSION_OK="no"
VIEWER_OK="no"
MANIFEST_OK="no"
METADATA_OK="n/a"
JOBS_JSON="[]"
JOBS_COUNT="0"
FILE_ID=""
CAD_VIEWER_URL=""
CAD_MANIFEST_URL=""
MANIFEST_ARTIFACTS="{}"
EXIT_CODE=0

write_report() {
  cat >"$REPORT_PATH" <<EOF
# CADGF Preview Online Verification Report

## Inputs
- BASE_URL: $BASE_URL
- TENANT/ORG: $TENANT / $ORG
- SAMPLE_FILE: $SAMPLE_FILE

## Results
- login_ok: $LOGIN_OK
- upload_ok: $UPLOAD_OK
- conversion_ok: $CONVERSION_OK
- viewer_load: $VIEWER_OK
- manifest_rewrite: $MANIFEST_OK
- metadata_present: $METADATA_OK
- jobs_count: $JOBS_COUNT
- file_id: $FILE_ID
- cad_viewer_url: $CAD_VIEWER_URL
- exit_code: $EXIT_CODE

## Jobs (import response)
\`\`\`json
$JOBS_JSON
\`\`\`

## Manifest Artifacts (rewrite=1)
\`\`\`json
$MANIFEST_ARTIFACTS
\`\`\`
EOF
}

finalize() {
  EXIT_CODE=$?
  write_report
  echo "report: $REPORT_PATH"
  exit "$EXIT_CODE"
}
trap finalize EXIT

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
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"$LOGIN_USERNAME\",\"password\":\"$PASSWORD\",\"org_id\":\"$ORG\"}")"
  AUTH_TOKEN="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))' <<<"$LOGIN_RESP")"
  if [[ -z "$AUTH_TOKEN" ]]; then
    echo "Login failed (no access_token). Provide AUTH_TOKEN or credentials." >&2
    exit 2
  fi
  AUTH_HEADER=(-H "Authorization: Bearer $AUTH_TOKEN")
fi
LOGIN_OK="yes"

HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

FILE_RESP="$($CURL -X POST "$BASE_URL/api/v1/cad/import" \
  "${HEADERS[@]}" "${AUTH_HEADER[@]}" \
  -F "file=@$SAMPLE_FILE;filename=$(basename "$SAMPLE_FILE")" \
  -F "create_preview_job=false" \
  -F "create_geometry_job=true" \
  -F "create_extract_job=false" \
  -F "create_dedup_job=false" \
  -F "create_ml_job=false")"
FILE_ID="$("$PY" -c 'import json,sys; data=json.load(sys.stdin); print(data.get("file_id") or data.get("id",""))' <<<"$FILE_RESP")"
if [[ -z "$FILE_ID" ]]; then
  echo "Upload failed: $FILE_RESP" >&2
  exit 1
fi
JOBS_JSON="$("$PY" -c 'import json,sys; data=json.load(sys.stdin); print(json.dumps(data.get("jobs", []), indent=2, sort_keys=True))' <<<"$FILE_RESP")"
JOBS_COUNT="$("$PY" -c 'import json,sys; data=json.load(sys.stdin); print(len(data.get("jobs", [])))' <<<"$FILE_RESP")"
UPLOAD_OK="yes"

for _ in {1..60}; do
  META_RESP="$($CURL "$BASE_URL/api/v1/file/$FILE_ID" "${HEADERS[@]}" "${AUTH_HEADER[@]}")"
  CAD_VIEWER_URL="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("cad_viewer_url",""))' <<<"$META_RESP")"
  CAD_MANIFEST_URL="$BASE_URL/api/v1/file/$FILE_ID/cad_manifest?rewrite=1"
  if [[ -n "$CAD_VIEWER_URL" && "$CAD_VIEWER_URL" != "None" ]]; then
    CONVERSION_OK="yes"
    break
  fi
  sleep 2
done

if [[ -z "$CAD_VIEWER_URL" || "$CAD_VIEWER_URL" == "None" ]]; then
  if [[ "$SYNC_GEOMETRY" == "1" ]]; then
    echo "cad_viewer_url missing; running cad_geometry synchronously" >&2
    export FILE_ID TENANT ORG
    "$PY" - <<'PY'
import json
import os
import sys

from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_geometry

tenant = os.environ.get("TENANT") or ""
org = os.environ.get("ORG") or ""
file_id = os.environ.get("FILE_ID")
if not file_id:
    sys.exit("missing FILE_ID for cad_geometry")

tenant_id_var.set(tenant)
org_id_var.set(org)
import_all_models()

with get_db_session() as session:
    result = cad_geometry({"file_id": file_id, "target_format": "gltf"}, session)

print(json.dumps(result))
if not result.get("ok"):
    sys.exit("cad_geometry failed")
PY

    META_RESP="$($CURL "$BASE_URL/api/v1/file/$FILE_ID" "${HEADERS[@]}" "${AUTH_HEADER[@]}")"
    CAD_VIEWER_URL="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("cad_viewer_url",""))' <<<"$META_RESP")"
    CAD_MANIFEST_URL="$BASE_URL/api/v1/file/$FILE_ID/cad_manifest?rewrite=1"
    if [[ -n "$CAD_VIEWER_URL" && "$CAD_VIEWER_URL" != "None" ]]; then
      CONVERSION_OK="yes"
    fi
  fi
fi

if [[ -n "$CAD_VIEWER_URL" && "$CAD_VIEWER_URL" != "None" ]]; then
  if $CURL "$CAD_VIEWER_URL" | grep -q "Web Preview"; then
    VIEWER_OK="yes"
  fi
fi

if [[ -n "$CAD_MANIFEST_URL" ]]; then
  MANIFEST_JSON="$($CURL "$CAD_MANIFEST_URL" "${HEADERS[@]}" "${AUTH_HEADER[@]}" || true)"
  MANIFEST_ARTIFACTS="$("$PY" -c $'import json,sys\nraw=sys.stdin.read().strip()\nif not raw:\n    print(\"{}\")\n    raise SystemExit(0)\ntry:\n    data=json.loads(raw)\nexcept Exception:\n    print(\"{}\")\n    raise SystemExit(0)\nif not isinstance(data, dict):\n    print(\"{}\")\n    raise SystemExit(0)\nprint(json.dumps(data.get(\"artifacts\", {}), indent=2, sort_keys=True))' <<<"$MANIFEST_JSON")"
  if echo "$MANIFEST_ARTIFACTS" | grep -q "http"; then
    MANIFEST_OK="yes"
  fi
  if [[ "${EXPECT_METADATA:-0}" == "1" ]]; then
    if echo "$MANIFEST_ARTIFACTS" | grep -q "\"mesh_metadata\""; then
      METADATA_OK="yes"
    else
      METADATA_OK="no"
      echo "Expected mesh_metadata in manifest artifacts but not found." >&2
      exit 1
    fi
  fi
fi
