#!/usr/bin/env bash
# =============================================================================
# CAD Auto Part Verification Script
# Verifies auto_create_part on /cad/import using extracted CAD attributes.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"
TENANCY_MODE_ENV="${YUANTUS_TENANCY_MODE:-}"
STORAGE_TYPE="${STORAGE_TYPE:-${YUANTUS_STORAGE_TYPE:-}}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-${YUANTUS_S3_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}}}"
S3_PUBLIC_ENDPOINT_URL="${S3_PUBLIC_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-${YUANTUS_S3_BUCKET_NAME:-}}"
S3_ACCESS_KEY_ID="${S3_ACCESS_KEY_ID:-${YUANTUS_S3_ACCESS_KEY_ID:-}}"
S3_SECRET_ACCESS_KEY="${S3_SECRET_ACCESS_KEY:-${YUANTUS_S3_SECRET_ACCESS_KEY:-}}"
LOCAL_STORAGE_PATH="${LOCAL_STORAGE_PATH:-${YUANTUS_LOCAL_STORAGE_PATH:-}}"

SAMPLE_FILE="${CAD_AUTO_SAMPLE_FILE:-}"
EXPECTED_ITEM_NUMBER="${CAD_AUTO_EXPECT_ITEM_NUMBER:-}"
EXPECTED_DESCRIPTION="${CAD_AUTO_EXPECT_DESCRIPTION:-}"
EXPECTED_REVISION="${CAD_AUTO_EXPECT_REVISION:-}"
CAD_FORMAT_OVERRIDE="${CAD_AUTO_CAD_FORMAT:-}"
CAD_CONNECTOR_OVERRIDE="${CAD_AUTO_CONNECTOR_ID:-}"
CAD_EXTRACTOR_BASE_URL="${CAD_EXTRACTOR_BASE_URL:-${YUANTUS_CAD_EXTRACTOR_BASE_URL:-}}"
CAD_EXTRACTOR_MODE="${CAD_EXTRACTOR_MODE:-${YUANTUS_CAD_EXTRACTOR_MODE:-}}"

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

TENANCY_MODE_HEALTH="$($CURL "$API/health" \
  | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("tenancy_mode",""))' 2>/dev/null || echo "")"

if [[ -z "$DB_URL" ]]; then
  if [[ -n "${YUANTUS_DATABASE_URL:-}" ]]; then
    DB_URL="$YUANTUS_DATABASE_URL"
  elif command -v docker >/dev/null 2>&1; then
    PORT_LINE="$(docker compose -p yuantusplm port postgres 5432 2>/dev/null | head -n 1)"
    if [[ -z "$PORT_LINE" ]]; then
      PORT_LINE="$(docker compose port postgres 5432 2>/dev/null | head -n 1)"
    fi
    if [[ -n "$PORT_LINE" ]]; then
      HOST_PORT="${PORT_LINE##*:}"
      DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:${HOST_PORT}/yuantus"
    fi
  fi
fi

if [[ -z "$TENANCY_MODE_ENV" && -n "$TENANCY_MODE_HEALTH" ]]; then
  export YUANTUS_TENANCY_MODE="$TENANCY_MODE_HEALTH"
  TENANCY_MODE_ENV="$TENANCY_MODE_HEALTH"
fi

if [[ -n "$DB_URL" && "$DB_URL" == postgresql* ]]; then
  DB_BASE="${DB_URL%/*}"
  if [[ -z "$DB_URL_TEMPLATE" ]]; then
    if [[ "$TENANCY_MODE_HEALTH" == "db-per-tenant-org" ]]; then
      DB_URL_TEMPLATE="${DB_BASE}/yuantus_mt_pg__{tenant_id}__{org_id}"
    elif [[ "$TENANCY_MODE_HEALTH" == "db-per-tenant" ]]; then
      DB_URL_TEMPLATE="${DB_BASE}/yuantus_mt_pg__{tenant_id}"
    fi
  fi
  if [[ -z "$IDENTITY_DB_URL" && "$TENANCY_MODE_HEALTH" != "single" ]]; then
    IDENTITY_DB_URL="${DB_BASE}/yuantus_identity_mt_pg"
  fi
fi

if [[ -n "$DB_URL" ]]; then
  export YUANTUS_DATABASE_URL="$DB_URL"
fi
if [[ -n "$DB_URL_TEMPLATE" ]]; then
  export DB_URL_TEMPLATE
  export YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"
fi
if [[ -n "$IDENTITY_DB_URL" ]]; then
  export IDENTITY_DB_URL
  export YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL"
fi

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$DB_URL" || -n "$identity_url" ]]; then
    env \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"} \
      ${TENANCY_MODE_ENV:+YUANTUS_TENANCY_MODE="$TENANCY_MODE_ENV"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      ${STORAGE_TYPE:+YUANTUS_STORAGE_TYPE="$STORAGE_TYPE"} \
      ${S3_ENDPOINT_URL:+YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL"} \
      ${S3_PUBLIC_ENDPOINT_URL:+YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL"} \
      ${S3_BUCKET_NAME:+YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME"} \
      ${S3_ACCESS_KEY_ID:+YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"} \
      ${S3_SECRET_ACCESS_KEY:+YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"} \
      ${LOCAL_STORAGE_PATH:+YUANTUS_LOCAL_STORAGE_PATH="$LOCAL_STORAGE_PATH"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

TS="$(date +%s)"
EXTRACTOR_CONFIGURED=""

EXTRACTOR_CONFIGURED="$($CURL "$API/health/deps" \
  2>/dev/null | "$PY" -c 'import sys,json; data=json.load(sys.stdin); print("1" if data.get("external", {}).get("cad_extractor", {}).get("configured") else "0")' 2>/dev/null || echo "")"

cleanup_file=0
if [[ -z "$SAMPLE_FILE" ]]; then
  AUTO_FILE_STEM="yuantus_cad_auto_part_$TS"
  SAMPLE_FILE="/tmp/${AUTO_FILE_STEM}.dwg"
  AUTO_PART_NUMBER="HC-$TS"
  cat > "$SAMPLE_FILE" <<DATA
# run_id=$TS
图号=$AUTO_PART_NUMBER
名称=浩辰CAD零件
版本=A
材料=钢
DATA
  cleanup_file=1
  if [[ -z "$CAD_FORMAT_OVERRIDE" ]]; then
    CAD_FORMAT_OVERRIDE="HAOCHEN"
  fi
  if [[ -z "$EXPECTED_ITEM_NUMBER" ]]; then
    if [[ -n "$CAD_EXTRACTOR_BASE_URL" || "$EXTRACTOR_CONFIGURED" == "1" ]]; then
      EXPECTED_ITEM_NUMBER="$AUTO_FILE_STEM"
    else
      EXPECTED_ITEM_NUMBER="$AUTO_PART_NUMBER"
    fi
  fi
  if [[ -z "$EXPECTED_DESCRIPTION" ]]; then
    if [[ -n "$CAD_EXTRACTOR_BASE_URL" || "$EXTRACTOR_CONFIGURED" == "1" ]]; then
      EXPECTED_DESCRIPTION=""
    else
      EXPECTED_DESCRIPTION="浩辰CAD零件"
    fi
  fi
fi

if [[ -z "$EXPECTED_ITEM_NUMBER" ]]; then
  fail "Missing CAD_AUTO_EXPECT_ITEM_NUMBER"
fi

if [[ -z "$SAMPLE_FILE" || ! -f "$SAMPLE_FILE" ]]; then
  fail "Missing CAD_AUTO_SAMPLE_FILE or file not found"
fi

EXTRA_FORMS=()
if [[ -n "$CAD_FORMAT_OVERRIDE" ]]; then
  EXTRA_FORMS+=( -F "cad_format=$CAD_FORMAT_OVERRIDE" )
fi
if [[ -n "$CAD_CONNECTOR_OVERRIDE" ]]; then
  EXTRA_FORMS+=( -F "cad_connector_id=$CAD_CONNECTOR_OVERRIDE" )
fi

FILENAME="$(basename "$SAMPLE_FILE")"

echo "=============================================="
echo "CAD Auto Part Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "SAMPLE: $SAMPLE_FILE"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login as admin"
ADMIN_TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

echo ""
echo "==> Fetch Part ItemType properties"
ITEMTYPE_JSON="$($CURL "$API/meta/item-types/Part" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
REV_PROP_ID="$(echo "$ITEMTYPE_JSON" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);props=d.get("properties",[]);print(next((p["id"] for p in props if p.get("name")=="revision"), ""))')"
if [[ -n "$EXPECTED_REVISION" && -z "$REV_PROP_ID" ]]; then
  fail "Missing revision property on Part (needed for CAD_AUTO_EXPECT_REVISION)"
fi
ok "Resolved property IDs"

echo ""
echo "==> Import CAD with auto_create_part"
IMPORT_RESP="$($CURL -X POST "$API/cad/import" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -F "file=@$SAMPLE_FILE;filename=$FILENAME" \
  -F "auto_create_part=true" \
  -F "create_extract_job=false" \
  -F "create_preview_job=false" \
  -F "create_geometry_job=false" \
  -F "create_dedup_job=false" \
  -F "create_ml_job=false" \
  "${EXTRA_FORMS[@]}")"
ITEM_ID="$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("item_id",""))')"
FILE_ID="$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')"
ATTACHMENT_ID="$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("attachment_id",""))')"
if [[ -z "$ITEM_ID" || -z "$FILE_ID" ]]; then
  echo "Response: $IMPORT_RESP" >&2
  fail "auto_create_part failed (missing item_id or file_id)"
fi
ok "Created/linked Part: $ITEM_ID"
ok "Imported File: $FILE_ID"
if [[ -n "$ATTACHMENT_ID" ]]; then
  ok "Attachment created: $ATTACHMENT_ID"
fi

echo ""
echo "==> Verify Part properties"
ITEM_JSON="$($CURL -X POST "$API/aml/apply" \
  -H 'content-type: application/json' \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -d "{\"type\":\"Part\",\"action\":\"get\",\"id\":\"$ITEM_ID\"}")"
RESP_JSON="$ITEM_JSON" EXPECTED_ITEM_NUMBER="$EXPECTED_ITEM_NUMBER" EXPECTED_DESCRIPTION="$EXPECTED_DESCRIPTION" EXPECTED_REVISION="$EXPECTED_REVISION" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "{}")
data = json.loads(raw)
items = data.get("items") or []
if not items:
    raise SystemExit("No items returned")
props = items[0].get("properties") or {}
expected_item = os.environ.get("EXPECTED_ITEM_NUMBER", "")
expected_desc = os.environ.get("EXPECTED_DESCRIPTION", "")
expected_rev = os.environ.get("EXPECTED_REVISION", "")
if expected_item and props.get("item_number") != expected_item:
    raise SystemExit(f"item_number mismatch: {props.get('item_number')}")
if expected_desc and props.get("description") != expected_desc:
    raise SystemExit(f"description mismatch: {props.get('description')}")
if expected_rev and props.get("revision") != expected_rev:
    raise SystemExit(f"revision mismatch: {props.get('revision')}")
print("Part properties verified")
PY
ok "Part properties verified"

echo ""
echo "==> Verify attachment list"
FILES_JSON="$($CURL "$API/file/item/$ITEM_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
RESP_JSON="$FILES_JSON" FILE_ID="$FILE_ID" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "[]")
items = json.loads(raw)
file_id = os.environ.get("FILE_ID")
if not any(it.get("file_id") == file_id for it in items):
    raise SystemExit("file attachment not found")
print("Attachment verified")
PY
ok "Attachment verified"

echo ""
echo "==> Cleanup"
if [[ "$cleanup_file" -eq 1 ]]; then
  rm -f "$SAMPLE_FILE"
  ok "Cleaned up temp file"
else
  ok "Skipped cleanup for CAD_AUTO_SAMPLE_FILE"
fi

echo ""
echo "=============================================="
echo "CAD Auto Part Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
