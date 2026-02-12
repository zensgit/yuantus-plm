#!/usr/bin/env bash
# =============================================================================
# CAD Dedup Vision Relationship Verification Script (S3)
#
# Verifies (end-to-end):
#   - create two Part items
#   - upload baseline 2D drawing (PNG) attached to Part A and index into Dedup Vision
#   - upload query 2D drawing (PNG) attached to Part B and search for baseline
#   - confirm SimilarityRecord is created and can be reviewed/confirmed
#   - auto-create Part Equivalent relationship (rule auto_create_relationship=true)
#   - verify equivalents API returns the relationship
#   - verify dedup batch run supports index=true and indexes a previously unindexed drawing
#   - verify dedupe promotion: pending search-only job is promoted to index=true
#
# Expected environment (defaults match docker-compose.yml host ports):
#   - Postgres: localhost:55432
#   - MinIO:    localhost:59000
#   - Dedup:    localhost:8100
#
# Usage:
#   docker compose -f docker-compose.yml --profile dedup up -d postgres minio api dedup-vision
#   docker compose -f docker-compose.yml --profile dedup up -d --build --no-deps api
#   scripts/verify_cad_dedup_relationship_s3.sh
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
CURL_FOLLOW="${CURL_FOLLOW:-curl -sSL}"

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"
TENANCY_MODE_ENV="${TENANCY_MODE_ENV:-${YUANTUS_TENANCY_MODE:-}}"

STORAGE_TYPE_ENV="${STORAGE_TYPE_ENV:-${YUANTUS_STORAGE_TYPE:-s3}}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-${YUANTUS_S3_ENDPOINT_URL:-http://localhost:59000}}"
S3_PUBLIC_ENDPOINT_URL="${S3_PUBLIC_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-http://localhost:59000}}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-${YUANTUS_S3_BUCKET_NAME:-yuantus}}"
S3_ACCESS_KEY_ID="${S3_ACCESS_KEY_ID:-${YUANTUS_S3_ACCESS_KEY_ID:-minioadmin}}"
S3_SECRET_ACCESS_KEY="${S3_SECRET_ACCESS_KEY:-${YUANTUS_S3_SECRET_ACCESS_KEY:-minioadmin}}"

DEDUP_BASE_URL="${DEDUP_BASE_URL:-${YUANTUS_DEDUP_VISION_BASE_URL:-http://localhost:8100}}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

if [[ ! -x "$CLI" ]]; then
  fail "Missing CLI at $CLI (set CLI=...)"
fi
if [[ ! -x "$PY" ]]; then
  fail "Missing Python at $PY (set PY=...)"
fi

run_cli() {
  env \
    YUANTUS_DATABASE_URL="$DB_URL" \
    YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL" \
    YUANTUS_STORAGE_TYPE="$STORAGE_TYPE_ENV" \
    YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL" \
    YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL" \
    YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME" \
    YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID" \
    YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY" \
    YUANTUS_DEDUP_VISION_BASE_URL="$DEDUP_BASE_URL" \
    ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"} \
    ${TENANCY_MODE_ENV:+YUANTUS_TENANCY_MODE="$TENANCY_MODE_ENV"} \
    "$CLI" "$@"
}

http_code() {
  # shellcheck disable=SC2086
  $CURL -o /dev/null -w "%{http_code}" "$@"
}

echo "=============================================="
echo "CAD Dedup Vision Relationship Verification (S3)"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "DB_URL: $DB_URL"
echo "S3_ENDPOINT_URL: $S3_ENDPOINT_URL"
echo "DEDUP_BASE_URL: $DEDUP_BASE_URL"
echo "=============================================="

echo ""
echo "==> Preflight: API health"
API_HEALTH_HTTP="$(http_code "$API/health" "${HEADERS[@]}")"
if [[ "$API_HEALTH_HTTP" != "200" ]]; then
  fail "API not healthy: $API/health (HTTP $API_HEALTH_HTTP)"
fi
ok "API is healthy"

echo ""
echo "==> Preflight: Dedup Vision health"
DEDUP_HEALTH_HTTP="$(http_code "$DEDUP_BASE_URL/health")"
if [[ "$DEDUP_HEALTH_HTTP" != "200" ]]; then
  fail "Dedup Vision not healthy: $DEDUP_BASE_URL/health (HTTP $DEDUP_HEALTH_HTTP)"
fi
ok "Dedup Vision is healthy"

if [[ "$STORAGE_TYPE_ENV" != "s3" ]]; then
  fail "This script expects S3 storage. Set YUANTUS_STORAGE_TYPE=s3 (got: $STORAGE_TYPE_ENV)"
fi

echo ""
echo "==> Seed identity (admin user)"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
ok "Identity seeded"

echo ""
echo "==> Seed meta schema"
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Meta schema seeded"

echo ""
echo "==> Login as admin"
ADMIN_TOKEN="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
ok "Admin login"
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")

# -----------------------------------------------------------------------------
# 1) Create rule: auto_create_relationship=true for 2D drawings
# -----------------------------------------------------------------------------
echo ""
echo "==> Create dedup rule (2d, auto_create_relationship=true, lenient thresholds)"
RULE_NAME="verify-dedup-rel-$(date +%s)"
RULE_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/dedup/rules" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{
      \"name\": \"${RULE_NAME}\",
      \"description\": \"Verification rule (auto-generated by scripts/verify_cad_dedup_relationship_s3.sh)\",
      \"document_type\": \"2d\",
      \"phash_threshold\": 64,
      \"feature_threshold\": 0.0,
      \"combined_threshold\": 0.0,
      \"detection_mode\": \"fast\",
      \"auto_create_relationship\": true,
      \"priority\": -1000,
      \"is_active\": true
    }"
)"
RULE_ID="$(echo "$RULE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$RULE_ID" ]]; then
  echo "Rule response: $RULE_RESP" >&2
  fail "Could not create dedup rule"
fi
ok "Dedup rule created: $RULE_ID ($RULE_NAME)"

# -----------------------------------------------------------------------------
# 2) Create two Part items
# -----------------------------------------------------------------------------
echo ""
echo "==> Create Part A and Part B via RPC"
ITEM_NO_A="VERIFY-DEDUP-A-$(date +%s)"
ITEM_NO_B="VERIFY-DEDUP-B-$(date +%s)"

PART_A_ID="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/rpc/" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{
      \"model\": \"Item\",
      \"method\": \"create\",
      \"args\": [{
        \"type\": \"Part\",
        \"properties\": {\"item_number\": \"${ITEM_NO_A}\", \"name\": \"Dedup Verify Part A\"}
      }],
      \"kwargs\": {}
    }" \
    | "$PY" -c 'import sys,json; d=json.load(sys.stdin); print((d.get("result") or {}).get("id") or "")'
)"
if [[ -z "$PART_A_ID" ]]; then
  fail "Could not create Part A"
fi
ok "Part A created: $PART_A_ID ($ITEM_NO_A)"

PART_B_ID="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/rpc/" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{
      \"model\": \"Item\",
      \"method\": \"create\",
      \"args\": [{
        \"type\": \"Part\",
        \"properties\": {\"item_number\": \"${ITEM_NO_B}\", \"name\": \"Dedup Verify Part B\"}
      }],
      \"kwargs\": {}
    }" \
    | "$PY" -c 'import sys,json; d=json.load(sys.stdin); print((d.get("result") or {}).get("id") or "")'
)"
if [[ -z "$PART_B_ID" ]]; then
  fail "Could not create Part B"
fi
ok "Part B created: $PART_B_ID ($ITEM_NO_B)"

# -----------------------------------------------------------------------------
# 3) Create test PNG pair
# -----------------------------------------------------------------------------
echo ""
echo "==> Create test PNG pair"
BASE_PNG="/tmp/yuantus_dedup_rel_base.png"
QUERY_PNG="/tmp/yuantus_dedup_rel_query.png"
PROMOTE_PNG="/tmp/yuantus_dedup_rel_promote.png"

"$PY" - << 'PY'
import struct, zlib, time
from pathlib import Path

def _chunk(tag: bytes, payload: bytes) -> bytes:
    length = struct.pack(">I", len(payload))
    crc = struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    return length + tag + payload + crc

def write_png(path: str, *, width: int, height: int, seed: int, tweak: bool, tweak2: bool=False) -> None:
    width = int(width)
    height = int(height)
    seed = int(seed)
    x0 = seed % 80 + 40
    y0 = (seed // 80) % 80 + 40
    x1 = (seed * 3) % 80 + 40
    y1 = (seed * 7) % 80 + 40
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    rows = []
    for y in range(height):
        row = bytearray()
        row.append(0)
        for x in range(width):
            v = 30
            if x % 32 == 0 or y % 32 == 0:
                v = 0
            if x0 <= x < x0 + 110 and y0 <= y < y0 + 70:
                v = 200
            if x1 <= x < x1 + 60 and y1 <= y < y1 + 40:
                v = 120
            if tweak and x == 5 and y == 5:
                v = 201
            if tweak2 and x == 6 and y == 5:
                v = 202
            row.extend((v, v, v))
        rows.append(bytes(row))
    raw = b"".join(rows)
    compressed = zlib.compress(raw)

    png = b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", ihdr),
            _chunk(b"IDAT", compressed),
            _chunk(b"IEND", b""),
        ]
    )
    Path(path).write_bytes(png)

seed = int(time.time())
# Make images unique per run to avoid checksum-based dedupe reusing old FileContainer rows
# with stale document_type values from earlier versions.
write_png("/tmp/yuantus_dedup_rel_base.png", width=256, height=256, seed=seed, tweak=False)
write_png("/tmp/yuantus_dedup_rel_query.png", width=256, height=256, seed=seed, tweak=True)
write_png("/tmp/yuantus_dedup_rel_promote.png", width=256, height=256, seed=seed, tweak=False, tweak2=True)
PY

if [[ ! -s "$BASE_PNG" || ! -s "$QUERY_PNG" || ! -s "$PROMOTE_PNG" ]]; then
  fail "PNG generation failed"
fi
ok "Created PNGs: $BASE_PNG, $QUERY_PNG, $PROMOTE_PNG"

# -----------------------------------------------------------------------------
# 4) Upload baseline (index=true) attached to Part A
# -----------------------------------------------------------------------------
echo ""
echo "==> Upload baseline PNG via /cad/import (dedup_index=true, attach Part A)"
IMPORT_BASE_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$BASE_PNG;filename=verify_dedup_rel_base.png" \
    -F "item_id=$PART_A_ID" \
    -F 'create_preview_job=false' \
    -F 'create_geometry_job=false' \
    -F 'create_dedup_job=true' \
    -F 'dedup_mode=fast' \
    -F 'dedup_index=true' \
    -F 'create_ml_job=false'
)"
BASE_FILE_ID="$(echo "$IMPORT_BASE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id","") or "")')"
if [[ -z "$BASE_FILE_ID" ]]; then
  echo "Import response: $IMPORT_BASE_RESP" >&2
  fail "Could not get baseline file_id"
fi
ok "Baseline file uploaded: $BASE_FILE_ID"

BASE_JOB_ID="$(
  echo "$IMPORT_BASE_RESP" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
for j in (d.get("jobs") or []):
    if j.get("task_type") == "cad_dedup_vision":
        print(j.get("id") or "")
        break
'
)"
if [[ -z "$BASE_JOB_ID" ]]; then
  fail "Could not get baseline cad_dedup_vision job id"
fi
echo "Baseline dedup job ID: $BASE_JOB_ID"

echo ""
echo "==> Run worker until baseline job completes"
for _ in {1..15}; do
  run_cli worker --worker-id cad-dedup-rel-verify --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null || \
  run_cli worker --worker-id cad-dedup-rel-verify --poll-interval 1 --once >/dev/null

  BASE_STATUS="$(
    # shellcheck disable=SC2086
    $CURL "$API/jobs/$BASE_JOB_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
      | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status","") or "")'
  )"
  echo "Baseline job status: $BASE_STATUS"
  if [[ "$BASE_STATUS" == "completed" || "$BASE_STATUS" == "failed" || "$BASE_STATUS" == "cancelled" ]]; then
    break
  fi
  sleep 1
done
if [[ "$BASE_STATUS" != "completed" ]]; then
  fail "Baseline job did not complete (status=$BASE_STATUS)"
fi
ok "Baseline job completed"

# -----------------------------------------------------------------------------
# 5) Upload query (index=false) attached to Part B
# -----------------------------------------------------------------------------
echo ""
echo "==> Upload query PNG via /cad/import (dedup_index=false, attach Part B)"
IMPORT_QUERY_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$QUERY_PNG;filename=verify_dedup_rel_query.png" \
    -F "item_id=$PART_B_ID" \
    -F 'create_preview_job=false' \
    -F 'create_geometry_job=false' \
    -F 'create_dedup_job=true' \
    -F 'dedup_mode=fast' \
    -F 'dedup_index=false' \
    -F 'create_ml_job=false'
)"
QUERY_FILE_ID="$(echo "$IMPORT_QUERY_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id","") or "")')"
if [[ -z "$QUERY_FILE_ID" ]]; then
  echo "Import response: $IMPORT_QUERY_RESP" >&2
  fail "Could not get query file_id"
fi
ok "Query file uploaded: $QUERY_FILE_ID"

QUERY_JOB_ID="$(
  echo "$IMPORT_QUERY_RESP" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
for j in (d.get("jobs") or []):
    if j.get("task_type") == "cad_dedup_vision":
        print(j.get("id") or "")
        break
'
)"
if [[ -z "$QUERY_JOB_ID" ]]; then
  fail "Could not get query cad_dedup_vision job id"
fi
echo "Query dedup job ID: $QUERY_JOB_ID"

echo ""
echo "==> Run worker until query job completes"
for _ in {1..15}; do
  run_cli worker --worker-id cad-dedup-rel-verify --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null || \
  run_cli worker --worker-id cad-dedup-rel-verify --poll-interval 1 --once >/dev/null

  QUERY_STATUS="$(
    # shellcheck disable=SC2086
    $CURL "$API/jobs/$QUERY_JOB_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
      | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status","") or "")'
  )"
  echo "Query job status: $QUERY_STATUS"
  if [[ "$QUERY_STATUS" == "completed" || "$QUERY_STATUS" == "failed" || "$QUERY_STATUS" == "cancelled" ]]; then
    break
  fi
  sleep 1
done
if [[ "$QUERY_STATUS" != "completed" ]]; then
  fail "Query job did not complete (status=$QUERY_STATUS)"
fi
ok "Query job completed"

# -----------------------------------------------------------------------------
# 6) Verify SimilarityRecord exists and confirm it => relationship created
# -----------------------------------------------------------------------------
echo ""
echo "==> Find SimilarityRecord for query->baseline"
REC_LIST="$(
  # shellcheck disable=SC2086
  $CURL "$API/dedup/records?source_file_id=$QUERY_FILE_ID&target_file_id=$BASE_FILE_ID&limit=5" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
REC_ID="$(echo "$REC_LIST" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
items=d.get("items") or []
print((items[0] or {}).get("id","") if items else "")
')"
if [[ -z "$REC_ID" ]]; then
  echo "Records response: $REC_LIST" >&2
  fail "No SimilarityRecord found"
fi
ok "SimilarityRecord found: $REC_ID"

echo ""
echo "==> Confirm SimilarityRecord (rule auto_create_relationship=true)"
REVIEW_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/dedup/records/$REC_ID/review" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d '{"status":"confirmed","comment":"verify relationship auto-create","create_relationship":false}'
)"
REL_ITEM_ID="$(echo "$REVIEW_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_item_id") or "")')"
if [[ -z "$REL_ITEM_ID" ]]; then
  echo "Review response: $REVIEW_RESP" >&2
  fail "relationship_item_id missing after confirm"
fi
ok "Relationship created: $REL_ITEM_ID"

echo ""
echo "==> Verify equivalents API shows Part A <-> Part B"
EQS_A="$(
  # shellcheck disable=SC2086
  $CURL "$API/items/$PART_A_ID/equivalents" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
echo "$EQS_A" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
eqs=d.get("equivalents") or []
ids=[(e or {}).get("equivalent_item_id") for e in eqs]
assert ids, d
assert "'"$PART_B_ID"'" in ids, ids
print("ok")
' >/dev/null
ok "Part A equivalents include Part B"

# -----------------------------------------------------------------------------
# 7) Verify batch run supports index=true and indexes query file (previously index=false)
# -----------------------------------------------------------------------------
echo ""
echo "==> Create dedup batch (scope=file_list => query file)"
BATCH_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/dedup/batches" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{
      \"name\": \"verify-dedup-batch-$(date +%s)\",
      \"description\": \"Verification batch (auto-generated)\",
      \"scope_type\": \"file_list\",
      \"scope_config\": {\"file_ids\": [\"$QUERY_FILE_ID\"]},
      \"rule_id\": \"$RULE_ID\"
    }"
)"
BATCH_ID="$(echo "$BATCH_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$BATCH_ID" ]]; then
  echo "Batch response: $BATCH_RESP" >&2
  fail "Could not create batch"
fi
ok "Batch created: $BATCH_ID"

echo ""
echo "==> Run batch (index=true)"
RUN_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/dedup/batches/$BATCH_ID/run" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d '{"mode":"fast","limit":10,"priority":30,"dedupe":true,"index":true}'
)"
JOBS_CREATED="$(echo "$RUN_RESP" | "$PY" -c 'import sys,json;print(int((json.load(sys.stdin).get("jobs_created") or 0)))')"
if [[ "$JOBS_CREATED" -lt 1 ]]; then
  echo "Run response: $RUN_RESP" >&2
  fail "Expected jobs_created >= 1"
fi
ok "Batch jobs created: $JOBS_CREATED"

echo ""
echo "==> Run worker until batch jobs complete"
for _ in {1..20}; do
  processed=false
  if run_cli worker --worker-id cad-dedup-rel-verify --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null; then
    processed=true
  elif run_cli worker --worker-id cad-dedup-rel-verify --poll-interval 1 --once >/dev/null; then
    processed=true
  fi
  if [[ "$processed" == "false" ]]; then
    break
  fi
  sleep 1
done
ok "Worker executed (batch indexing)"

echo ""
echo "==> Verify query cad_dedup payload now has indexed.success=true"
QUERY_META="$(
  # shellcheck disable=SC2086
  $CURL "$API/file/$QUERY_FILE_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
QUERY_CAD_DEDUP_URL="$(echo "$QUERY_META" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("cad_dedup_url",""))')"
if [[ -z "$QUERY_CAD_DEDUP_URL" ]]; then
  echo "File meta: $QUERY_META" >&2
  fail "Query cad_dedup_url missing"
fi
QUERY_DEDUP_PAYLOAD="$(
  # shellcheck disable=SC2086
  $CURL_FOLLOW "$BASE_URL$QUERY_CAD_DEDUP_URL" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
echo "$QUERY_DEDUP_PAYLOAD" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
indexed=d.get("indexed") or {}
assert indexed.get("success") is True, indexed
print("ok")
' >/dev/null
ok "Query cad_dedup indexed.success=true"

# -----------------------------------------------------------------------------
# 8) Verify promotion: pending search-only job promoted to index=true
# -----------------------------------------------------------------------------
echo ""
echo "==> Promotion test: create pending job with dedup_index=false, then promote via dedup_index=true"

PROMOTE_IMPORT_1="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$PROMOTE_PNG;filename=verify_dedup_rel_promote.png" \
    -F "item_id=$PART_A_ID" \
    -F 'create_preview_job=false' \
    -F 'create_geometry_job=false' \
    -F 'create_dedup_job=true' \
    -F 'dedup_mode=fast' \
    -F 'dedup_index=false' \
    -F 'create_ml_job=false'
)"
PROMOTE_FILE_ID="$(
  echo "$PROMOTE_IMPORT_1" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))'
)"
PROMOTE_JOB_ID="$(
  echo "$PROMOTE_IMPORT_1" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
for j in (d.get("jobs") or []):
    if j.get("task_type") == "cad_dedup_vision":
        print(j.get("id") or "")
        break
'
)"
if [[ -z "$PROMOTE_FILE_ID" || -z "$PROMOTE_JOB_ID" ]]; then
  echo "Import response: $PROMOTE_IMPORT_1" >&2
  fail "Promotion initial import missing file_id/job_id"
fi
ok "Promotion baseline created: file=$PROMOTE_FILE_ID job=$PROMOTE_JOB_ID (index=false)"

# Immediately call import again (same bytes) but ask for index=true.
PROMOTE_IMPORT_2="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$PROMOTE_PNG;filename=verify_dedup_rel_promote.png" \
    -F "item_id=$PART_A_ID" \
    -F 'create_preview_job=false' \
    -F 'create_geometry_job=false' \
    -F 'create_dedup_job=true' \
    -F 'dedup_mode=fast' \
    -F 'dedup_index=true' \
    -F 'create_ml_job=false'
)"
PROMOTE_JOB_ID_2="$(
  echo "$PROMOTE_IMPORT_2" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
for j in (d.get("jobs") or []):
    if j.get("task_type") == "cad_dedup_vision":
        print(j.get("id") or "")
        break
'
)"
if [[ -z "$PROMOTE_JOB_ID_2" ]]; then
  echo "Import response: $PROMOTE_IMPORT_2" >&2
  fail "Promotion second import missing job id"
fi
if [[ "$PROMOTE_JOB_ID_2" != "$PROMOTE_JOB_ID" ]]; then
  fail "Expected promotion to reuse the pending job id (got $PROMOTE_JOB_ID_2, expected $PROMOTE_JOB_ID)"
fi
ok "Promotion reused same pending job: $PROMOTE_JOB_ID"

PROMOTE_JOB_PAYLOAD="$(
  # shellcheck disable=SC2086
  $CURL "$API/jobs/$PROMOTE_JOB_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
echo "$PROMOTE_JOB_PAYLOAD" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
p=d.get("payload") or {}
assert bool(p.get("index", False)) is True, p
print("ok")
' >/dev/null
ok "Pending job payload promoted to index=true"

echo ""
echo "==> Run worker until promoted job completes"
for _ in {1..15}; do
  run_cli worker --worker-id cad-dedup-rel-verify --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null || \
  run_cli worker --worker-id cad-dedup-rel-verify --poll-interval 1 --once >/dev/null

  STATUS="$(
    # shellcheck disable=SC2086
    $CURL "$API/jobs/$PROMOTE_JOB_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
      | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status","") or "")'
  )"
  echo "Promoted job status: $STATUS"
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" || "$STATUS" == "cancelled" ]]; then
    break
  fi
  sleep 1
done
if [[ "$STATUS" != "completed" ]]; then
  fail "Promoted job did not complete (status=$STATUS)"
fi
ok "Promoted job completed"

echo ""
echo "==> Verify promoted file cad_dedup indexed.success=true"
PROMOTE_META="$(
  # shellcheck disable=SC2086
  $CURL "$API/file/$PROMOTE_FILE_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
PROMOTE_CAD_DEDUP_URL="$(echo "$PROMOTE_META" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("cad_dedup_url",""))')"
if [[ -z "$PROMOTE_CAD_DEDUP_URL" ]]; then
  echo "File meta: $PROMOTE_META" >&2
  fail "Promote cad_dedup_url missing"
fi
PROMOTE_DEDUP_PAYLOAD="$(
  # shellcheck disable=SC2086
  $CURL_FOLLOW "$BASE_URL$PROMOTE_CAD_DEDUP_URL" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
echo "$PROMOTE_DEDUP_PAYLOAD" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
indexed=d.get("indexed") or {}
assert indexed.get("success") is True, indexed
print("ok")
' >/dev/null
ok "Promoted file indexed.success=true"

echo ""
echo "ALL CHECKS PASSED"
