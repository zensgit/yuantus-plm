#!/usr/bin/env bash
# =============================================================================
# CAD 2D Real Connector Verification Script
# Verifies real DWG uploads with explicit Haochen/Zhongwang connector overrides,
# and validates extracted attributes (part_number/drawing_no) from filename.
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

CAD_EXTRACTOR_BASE_URL="${CAD_EXTRACTOR_BASE_URL:-${YUANTUS_CAD_EXTRACTOR_BASE_URL:-}}"
CAD_EXTRACTOR_MODE="${CAD_EXTRACTOR_MODE:-${YUANTUS_CAD_EXTRACTOR_MODE:-}}"

CAD_SAMPLE_HAOCHEN_DWG="${CAD_SAMPLE_HAOCHEN_DWG:-/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg}"
CAD_SAMPLE_ZHONGWANG_DWG="${CAD_SAMPLE_ZHONGWANG_DWG:-/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg}"
CAD_REAL_FORCE_UNIQUE="${CAD_REAL_FORCE_UNIQUE:-1}"

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
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      ${TENANCY_MODE_ENV:+YUANTUS_TENANCY_MODE="$TENANCY_MODE_ENV"} \
      ${STORAGE_TYPE:+YUANTUS_STORAGE_TYPE="$STORAGE_TYPE"} \
      ${S3_ENDPOINT_URL:+YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL"} \
      ${S3_PUBLIC_ENDPOINT_URL:+YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL"} \
      ${S3_BUCKET_NAME:+YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME"} \
      ${S3_ACCESS_KEY_ID:+YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"} \
      ${S3_SECRET_ACCESS_KEY:+YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"} \
      ${LOCAL_STORAGE_PATH:+YUANTUS_LOCAL_STORAGE_PATH="$LOCAL_STORAGE_PATH"} \
      ${CAD_EXTRACTOR_BASE_URL:+YUANTUS_CAD_EXTRACTOR_BASE_URL="$CAD_EXTRACTOR_BASE_URL"} \
      ${CAD_EXTRACTOR_MODE:+YUANTUS_CAD_EXTRACTOR_MODE="$CAD_EXTRACTOR_MODE"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

make_unique_copy() {
  local src="$1"
  local label="$2"
  local tmp="/tmp/yuantus_real_${label}_$(date +%s)_$$.dwg"
  "$PY" - "$src" "$tmp" <<'PY'
import os
import shutil
import sys

src = sys.argv[1]
dst = sys.argv[2]
shutil.copyfile(src, dst)
with open(dst, "ab") as f:
    f.write(b"\nYUANTUS_REAL_SAMPLE\n")
PY
  echo "$tmp"
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

wait_for_job() {
  local job_id="$1"
  local status=""
  local completed=0
  for _ in {1..5}; do
    run_cli worker --worker-id cad-2d-real --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null || \
    run_cli worker --worker-id cad-2d-real --poll-interval 1 --once >/dev/null
    status="$($CURL "$API/jobs/$job_id" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
      | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status",""))')"
    if [[ "$status" == "completed" ]]; then
      completed=1
      ok "Job completed"
      break
    fi
    sleep 1
  done
  if [[ "$completed" -ne 1 ]]; then
    echo "Worker did not complete job (status=$status). Running direct processor..."
    env \
      JOB_ID="$job_id" TENANT="$TENANT" ORG="$ORG" \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"} \
      ${IDENTITY_DB_URL:+YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL"} \
      ${TENANCY_MODE_ENV:+YUANTUS_TENANCY_MODE="$TENANCY_MODE_ENV"} \
      ${STORAGE_TYPE:+YUANTUS_STORAGE_TYPE="$STORAGE_TYPE"} \
      ${S3_ENDPOINT_URL:+YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL"} \
      ${S3_PUBLIC_ENDPOINT_URL:+YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL"} \
      ${S3_BUCKET_NAME:+YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME"} \
      ${S3_ACCESS_KEY_ID:+YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"} \
      ${S3_SECRET_ACCESS_KEY:+YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"} \
      ${LOCAL_STORAGE_PATH:+YUANTUS_LOCAL_STORAGE_PATH="$LOCAL_STORAGE_PATH"} \
      ${CAD_EXTRACTOR_BASE_URL:+YUANTUS_CAD_EXTRACTOR_BASE_URL="$CAD_EXTRACTOR_BASE_URL"} \
      ${CAD_EXTRACTOR_MODE:+YUANTUS_CAD_EXTRACTOR_MODE="$CAD_EXTRACTOR_MODE"} \
      "$PY" - <<'PY'
import os
from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_extract

job_id = os.environ.get("JOB_ID")
tenant = os.environ.get("TENANT")
org = os.environ.get("ORG")
if not job_id or not tenant or not org:
    raise SystemExit("Missing JOB_ID/TENANT/ORG for direct processor")

tenant_id_var.set(tenant)
org_id_var.set(org)
import_all_models()
with get_db_session() as session:
    svc = JobService(session)
    job = svc.get_job(job_id)
    if not job:
        raise SystemExit("Job not found")
    cad_extract(job.payload or {}, session)
    svc.complete_job(job_id, result={"ok": True})
PY
  fi
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

if [[ ! -f "$CAD_SAMPLE_HAOCHEN_DWG" && ! -f "$CAD_SAMPLE_ZHONGWANG_DWG" ]]; then
  echo "SKIP: No CAD samples found. Set CAD_SAMPLE_HAOCHEN_DWG/CAD_SAMPLE_ZHONGWANG_DWG." >&2
  exit 0
fi

echo "=============================================="
echo "CAD 2D Real Connectors Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "HAOCHEN: $CAD_SAMPLE_HAOCHEN_DWG"
echo "ZHONGWANG: $CAD_SAMPLE_ZHONGWANG_DWG"
echo "CAD_EXTRACTOR_BASE_URL: ${CAD_EXTRACTOR_BASE_URL:-}"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login as admin"
ADMIN_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

verify_real() {
  local label="$1"
  local file_path="$2"
  local cad_format="$3"
  local connector_id="$4"
  local upload_path="$file_path"
  local cleanup_upload=0

  if [[ ! -f "$file_path" ]]; then
    echo "SKIP: $label sample not found: $file_path"
    return 0
  fi

  if [[ "$CAD_REAL_FORCE_UNIQUE" == "1" ]]; then
    upload_path="$(make_unique_copy "$file_path" "$label")"
    cleanup_upload=1
  fi

  local expect_json
  expect_json="$(resolve_expectations "$file_path")"
  local expected_prefix
  expected_prefix="$(echo "$expect_json" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["prefix"])')"
  local expected_revision
  expected_revision="$(echo "$expect_json" | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["revision"])')"

  echo ""
  echo "==> [$label] Upload + cad_extract"
  IMPORT_RESP="$(
    $CURL -X POST "$API/cad/import" \
      "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
      -F "file=@$upload_path;filename=$(basename "$file_path")" \
      -F "cad_format=$cad_format" \
      -F "cad_connector_id=$connector_id" \
      -F "create_extract_job=true" \
      -F "create_preview_job=false" \
      -F "create_geometry_job=false" \
      -F "create_dedup_job=false" \
      -F "create_ml_job=false"
  )"
  FILE_ID="$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')"
  JOB_ID="$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);print(next((j.get("id") for j in d.get("jobs",[]) if j.get("task_type")=="cad_extract"), ""))')"
  if [[ -z "$FILE_ID" || -z "$JOB_ID" ]]; then
    echo "Response: $IMPORT_RESP" >&2
    fail "Failed to enqueue cad_extract job ($label)"
  fi
  ok "$label uploaded (file_id=$FILE_ID, job_id=$JOB_ID)"

  wait_for_job "$JOB_ID"

  META="$($CURL "$API/file/$FILE_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
  RESP_JSON="$META" EXPECT_VENDOR="$cad_format" EXPECT_CONNECTOR="$connector_id" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
data = json.loads(raw)
vendor = data.get("cad_format")
doc_type = data.get("document_type")
connector = data.get("cad_connector_id")
expected_vendor = os.environ.get("EXPECT_VENDOR")
expected_connector = os.environ.get("EXPECT_CONNECTOR")
if vendor != expected_vendor:
    raise SystemExit(f"cad_format mismatch: {vendor} != {expected_vendor}")
if doc_type != "2d":
    raise SystemExit(f"document_type mismatch: {doc_type} != 2d")
if expected_connector and connector != expected_connector:
    raise SystemExit(f"cad_connector_id mismatch: {connector} != {expected_connector}")
print("Metadata OK")
PY
  ok "$label metadata verified"

  ATTR_RESP="$($CURL "$API/cad/files/$FILE_ID/attributes" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
  RESP_JSON="$ATTR_RESP" EXPECT_PART="$expected_prefix" EXPECT_REV="$expected_revision" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
data = json.loads(raw)
attrs = data.get("extracted_attributes") or {}
part = attrs.get("part_number")
drawing = attrs.get("drawing_no")
expected_part = os.environ.get("EXPECT_PART")
expected_rev = os.environ.get("EXPECT_REV")
if part != expected_part:
    raise SystemExit(f"part_number mismatch: {part} != {expected_part}")
if drawing != expected_part:
    raise SystemExit(f"drawing_no mismatch: {drawing} != {expected_part}")
if expected_rev:
    rev = attrs.get("revision")
    if rev is not None and str(rev) != expected_rev:
        raise SystemExit(f"revision mismatch: {rev} != {expected_rev}")
print("Attributes OK")
PY
  ok "$label attributes verified (part_number=$expected_prefix)"

  if [[ "$cleanup_upload" -eq 1 ]]; then
    rm -f "$upload_path"
  fi
}

verify_real "HAOCHEN" "$CAD_SAMPLE_HAOCHEN_DWG" "HAOCHEN" "haochencad"
verify_real "ZHONGWANG" "$CAD_SAMPLE_ZHONGWANG_DWG" "ZHONGWANG" "zhongwangcad"

echo ""
echo "=============================================="
echo "CAD 2D Real Connectors Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
