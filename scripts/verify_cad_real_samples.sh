#!/usr/bin/env bash
# =============================================================================
# CAD Real Samples Verification Script
# Verifies import -> extract -> preview -> auto part for real DWG/STEP/PRT files.
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

CAD_EXTRACTOR_BASE_URL="${CAD_EXTRACTOR_BASE_URL:-${YUANTUS_CAD_EXTRACTOR_BASE_URL:-http://localhost:8200}}"
CAD_EXTRACTOR_MODE="${CAD_EXTRACTOR_MODE:-${YUANTUS_CAD_EXTRACTOR_MODE:-}}"
CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-${YUANTUS_CAD_ML_BASE_URL:-http://localhost:8001}}"
CAD_ML_TOKEN="${CAD_ML_SERVICE_TOKEN:-${YUANTUS_CAD_ML_SERVICE_TOKEN:-}}"

CAD_SAMPLE_DWG="${CAD_SAMPLE_DWG:-/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg}"
CAD_SAMPLE_STEP="${CAD_SAMPLE_STEP:-/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp}"
CAD_SAMPLE_PRT="${CAD_SAMPLE_PRT:-/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt}"

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

normalize_http_code() {
  local http_code="${1:-}"
  if [[ ! "$http_code" =~ ^[0-9]{3}$ ]]; then
    echo "000"
    return 0
  fi
  echo "$http_code"
}

seed_meta() {
  run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
  run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
}

admin_login() {
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
}

resolve_expectations() {
  FILE_PATH="$1" "$PY" - <<'PY'
import json
import os
import re
from pathlib import Path

path = Path(os.environ["FILE_PATH"])
stem = path.stem
prefix_match = re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*", stem)
prefix = prefix_match.group(0) if prefix_match else stem
rev_match = re.search(r"(?i)v(\d+(?:\.\d+)*)$", stem)
revision = f"v{rev_match.group(1)}" if rev_match else ""
print(json.dumps({"prefix": prefix, "revision": revision, "stem": stem}))
PY
}

run_cad_extract() {
  "$PY" - <<'PY'
import os

from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_extract

file_id = os.environ.get("FILE_ID")
tenant = os.environ.get("TENANT")
org = os.environ.get("ORG")

if not file_id:
    raise SystemExit("Missing FILE_ID")

tenant_id_var.set(tenant)
org_id_var.set(org)
import_all_models()

with get_db_session() as session:
    result = cad_extract({"file_id": file_id}, session)
    if not result.get("ok"):
        raise SystemExit("cad_extract failed")
PY
}

run_cad_preview() {
  "$PY" - <<'PY'
import os

from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_preview

file_id = os.environ.get("FILE_ID")
tenant = os.environ.get("TENANT")
org = os.environ.get("ORG")

if not file_id:
    raise SystemExit("Missing FILE_ID")

tenant_id_var.set(tenant)
org_id_var.set(org)
import_all_models()

with get_db_session() as session:
    result = cad_preview({"file_id": file_id}, session)
    if not result.get("ok"):
        raise SystemExit("cad_preview failed")
PY
}

verify_sample() {
  local label="$1"
  local file_path="$2"

  if [[ ! -f "$file_path" ]]; then
    echo "SKIP: $label sample not found: $file_path"
    return 0
  fi

  local expect_json
  expect_json="$(resolve_expectations "$file_path")"
  local expected_prefix expected_revision
  expected_prefix="$(echo "$expect_json" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["prefix"])')"
  expected_revision="$(echo "$expect_json" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["revision"])')"

  echo ""
  echo "==> [$label] Import + auto_create_part"
  local import_resp file_id item_id
  import_resp="$($CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$file_path;filename=$(basename "$file_path")" \
    -F "auto_create_part=true" \
    -F "create_extract_job=false" \
    -F "create_preview_job=false" \
    -F "create_geometry_job=false" \
    -F "create_dedup_job=false" \
    -F "create_ml_job=false")"

  file_id=$(echo "$import_resp" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')
  item_id=$(echo "$import_resp" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("item_id",""))')
  if [[ -z "$file_id" || -z "$item_id" ]]; then
    echo "Response: $import_resp" >&2
    fail "$label import failed (missing file_id or item_id)"
  fi
  ok "$label imported (file_id=$file_id, item_id=$item_id)"

  export FILE_ID="$file_id" TENANT="$TENANT" ORG="$ORG"
  if [[ -n "$DB_URL" ]]; then
    export YUANTUS_DATABASE_URL="$DB_URL"
  fi
  if [[ -n "$DB_URL_TEMPLATE" ]]; then
    export YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"
  fi
  if [[ -n "$IDENTITY_DB_URL" ]]; then
    export YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL"
  fi
  if [[ -n "$STORAGE_TYPE" ]]; then
    export YUANTUS_STORAGE_TYPE="$STORAGE_TYPE"
  fi
  if [[ -n "$S3_ENDPOINT_URL" ]]; then
    export YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL"
  fi
  if [[ -n "$S3_PUBLIC_ENDPOINT_URL" ]]; then
    export YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL"
  fi
  if [[ -n "$S3_BUCKET_NAME" ]]; then
    export YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME"
  fi
  if [[ -n "$S3_ACCESS_KEY_ID" ]]; then
    export YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"
  fi
  if [[ -n "$S3_SECRET_ACCESS_KEY" ]]; then
    export YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"
  fi
  if [[ -n "$LOCAL_STORAGE_PATH" ]]; then
    export YUANTUS_LOCAL_STORAGE_PATH="$LOCAL_STORAGE_PATH"
  fi
  if [[ -n "$CAD_EXTRACTOR_BASE_URL" ]]; then
    export YUANTUS_CAD_EXTRACTOR_BASE_URL="$CAD_EXTRACTOR_BASE_URL"
  fi
  if [[ -n "$CAD_EXTRACTOR_MODE" ]]; then
    export YUANTUS_CAD_EXTRACTOR_MODE="$CAD_EXTRACTOR_MODE"
  fi
  if [[ -n "$CAD_ML_BASE_URL" ]]; then
    export YUANTUS_CAD_ML_BASE_URL="$CAD_ML_BASE_URL"
  fi
  if [[ -n "$CAD_ML_TOKEN" ]]; then
    export YUANTUS_CAD_ML_SERVICE_TOKEN="$CAD_ML_TOKEN"
  fi

  echo "==> [$label] Run cad_extract"
  run_cad_extract
  ok "$label cad_extract OK"

  echo "==> [$label] Run cad_preview"
  run_cad_preview
  ok "$label cad_preview OK"

  echo "==> [$label] Verify preview endpoint"
  local preview_code
  preview_code="$($CURL -o /dev/null -w '%{http_code}' \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    "$BASE_URL/api/v1/file/$file_id/preview" 2>/dev/null || true)"
  preview_code="$(normalize_http_code "$preview_code")"
  if [[ "$preview_code" != "200" && "$preview_code" != "302" ]]; then
    fail "$label preview endpoint returned HTTP $preview_code"
  fi
  ok "$label preview endpoint HTTP $preview_code"

  echo "==> [$label] Verify extracted attributes"
  local attr_json
  attr_json="$($CURL "$API/cad/files/$file_id/attributes" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
  RESP_JSON="$attr_json" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("RESP_JSON", "{}")
resp = json.loads(raw)
attrs = resp.get("extracted_attributes") or {}
source = resp.get("source")
if not source:
    raise SystemExit("missing source")
if not isinstance(attrs, dict) or not attrs:
    raise SystemExit("empty attributes")
PY
  ok "$label attributes OK"

  echo "==> [$label] Verify auto-created Part"
  local item_json
  item_json="$($CURL -X POST "$API/aml/apply" \
    -H 'content-type: application/json' \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"get\",\"id\":\"$item_id\"}")"
  RESP_JSON="$item_json" EXPECT_PREFIX="$expected_prefix" EXPECT_REV="$expected_revision" "$PY" - <<'PY'
import os
import json

raw = os.environ.get("RESP_JSON", "{}")
expected_prefix = os.environ.get("EXPECT_PREFIX", "")
expected_rev = os.environ.get("EXPECT_REV", "")

payload = json.loads(raw)
items = payload.get("items") or []
if not items:
    raise SystemExit("no item returned")
props = items[0].get("properties") or {}
item_number = str(props.get("item_number") or "").strip()
if expected_prefix and item_number != expected_prefix:
    raise SystemExit(f"item_number mismatch: {item_number} != {expected_prefix}")
if expected_rev:
    revision = str(props.get("revision") or "").strip()
    if revision != expected_rev:
        raise SystemExit(f"revision mismatch: {revision} != {expected_rev}")
PY
  ok "$label Part properties OK (item_number=$expected_prefix)"
}

TENANCY_MODE_HEALTH="$($CURL "$API/health" \
  | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("tenancy_mode",""))' 2>/dev/null || echo "")"

if [[ -z "$TENANCY_MODE_ENV" && -n "$TENANCY_MODE_HEALTH" ]]; then
  export YUANTUS_TENANCY_MODE="$TENANCY_MODE_HEALTH"
  TENANCY_MODE_ENV="$TENANCY_MODE_HEALTH"
fi

if [[ -z "$DB_URL" && -n "${YUANTUS_DATABASE_URL:-}" ]]; then
  DB_URL="$YUANTUS_DATABASE_URL"
fi

if [[ -z "$DB_URL" && -n "$TENANCY_MODE_HEALTH" ]] && command -v docker >/dev/null 2>&1; then
  PORT_LINE="$(docker compose -p yuantusplm port postgres 5432 2>/dev/null | head -n 1 || true)"
  if [[ -z "$PORT_LINE" ]]; then
    PORT_LINE="$(docker compose port postgres 5432 2>/dev/null | head -n 1 || true)"
  fi
  if [[ -n "$PORT_LINE" ]]; then
    HOST_PORT="${PORT_LINE##*:}"
    DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:${HOST_PORT}/yuantus"
  fi
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
  export YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"
fi
if [[ -n "$IDENTITY_DB_URL" ]]; then
  export YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL"
fi

if [[ -n "$STORAGE_TYPE" ]]; then
  export YUANTUS_STORAGE_TYPE="$STORAGE_TYPE"
fi
if [[ -n "$S3_ENDPOINT_URL" ]]; then
  export YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL"
fi
if [[ -n "$S3_PUBLIC_ENDPOINT_URL" ]]; then
  export YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL"
fi
if [[ -n "$S3_BUCKET_NAME" ]]; then
  export YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME"
fi
if [[ -n "$S3_ACCESS_KEY_ID" ]]; then
  export YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"
fi
if [[ -n "$S3_SECRET_ACCESS_KEY" ]]; then
  export YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"
fi
if [[ -n "$CAD_EXTRACTOR_BASE_URL" ]]; then
  export YUANTUS_CAD_EXTRACTOR_BASE_URL="$CAD_EXTRACTOR_BASE_URL"
fi
if [[ -n "$CAD_EXTRACTOR_MODE" ]]; then
  export YUANTUS_CAD_EXTRACTOR_MODE="$CAD_EXTRACTOR_MODE"
fi
if [[ -n "$CAD_ML_BASE_URL" ]]; then
  export YUANTUS_CAD_ML_BASE_URL="$CAD_ML_BASE_URL"
fi
if [[ -n "$CAD_ML_TOKEN" ]]; then
  export YUANTUS_CAD_ML_SERVICE_TOKEN="$CAD_ML_TOKEN"
fi

if [[ ! -f "$CAD_SAMPLE_DWG" && ! -f "$CAD_SAMPLE_STEP" && ! -f "$CAD_SAMPLE_PRT" ]]; then
  echo "SKIP: No CAD samples found. Set CAD_SAMPLE_DWG/STEP/PRT." >&2
  exit 0
fi

if [[ -z "$CAD_EXTRACTOR_BASE_URL" ]]; then
  echo "WARN: CAD_EXTRACTOR_BASE_URL not set; extraction may use local fallback." >&2
fi

echo "=============================================="
echo "CAD Real Samples Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "DWG: $CAD_SAMPLE_DWG"
echo "STEP: $CAD_SAMPLE_STEP"
echo "PRT: $CAD_SAMPLE_PRT"
echo "CAD_EXTRACTOR_BASE_URL: ${CAD_EXTRACTOR_BASE_URL:-}"
echo "=============================================="

seed_meta
ok "Seeded identity/meta"

ADMIN_TOKEN="$(admin_login)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

verify_sample "DWG" "$CAD_SAMPLE_DWG"
verify_sample "STEP" "$CAD_SAMPLE_STEP"
verify_sample "PRT" "$CAD_SAMPLE_PRT"

echo ""
echo "=============================================="
echo "CAD Real Samples Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
