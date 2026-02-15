#!/usr/bin/env bash
# =============================================================================
# CAD Dedup Vision Verification Script (S3)
#
# Verifies (end-to-end):
#   - upload 2D drawing (PNG) via /api/v1/cad/import
#   - enqueue cad_dedup_vision job (optionally indexes into Dedup Vision)
#   - process job via `yuantus worker`
#   - persist cad_dedup payload to storage and expose via /api/v1/file/{id}/cad_dedup
#   - confirm a second query drawing finds at least one match (baseline drawing)
#
# Expected environment (defaults match docker-compose.yml host ports):
#   - Postgres: localhost:55432
#   - MinIO:    localhost:59000
#   - Dedup:    localhost:8100
#
# Usage:
#   docker compose -f docker-compose.yml --profile dedup up -d postgres minio api dedup-vision
#   # Mode A: local worker via CLI (--once)
#   scripts/verify_cad_dedup_vision_s3.sh
#   # Mode B: docker worker container (more production-like)
#   docker compose -f docker-compose.yml --profile dedup up -d worker
#   USE_DOCKER_WORKER=1 scripts/verify_cad_dedup_vision_s3.sh
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

DEDUP_BASE_URL="${DEDUP_BASE_URL:-${YUANTUS_DEDUP_VISION_BASE_URL:-${YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL:-http://localhost:${DEDUP_VISION_PORT:-8100}}}}"
USE_DOCKER_WORKER="${USE_DOCKER_WORKER:-0}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|y|Y|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

USE_DOCKER_WORKER_ENABLED=false
if is_truthy "$USE_DOCKER_WORKER"; then
  USE_DOCKER_WORKER_ENABLED=true
fi

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

pump_local_worker_once() {
  if [[ "$USE_DOCKER_WORKER_ENABLED" == "true" ]]; then
    return 0
  fi

  run_cli worker --worker-id cad-dedup-verify --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null 2>&1 || \
  run_cli worker --worker-id cad-dedup-verify --poll-interval 1 --once >/dev/null 2>&1 || \
  true
}

wait_for_job_completed() {
  local job_id="$1"
  local label="$2"
  local timeout_s="${3:-180}"
  local poll_s="${4:-2}"

  local start
  start="$(date +%s)"

  while true; do
    pump_local_worker_once

    local job_json status
    # shellcheck disable=SC2086
    job_json="$($CURL "$API/jobs/$job_id" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
    status="$(echo "$job_json" | "$PY" -c 'import sys,json; print((json.load(sys.stdin).get("status") or ""))')"
    echo "${label} status: ${status}"

    if [[ "$status" == "completed" || "$status" == "failed" || "$status" == "cancelled" ]]; then
      if [[ "$status" != "completed" ]]; then
        fail "${label} did not complete (status=$status)"
      fi

      local ok_flag err
      ok_flag="$(echo "$job_json" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
r=(d.get("payload") or {}).get("result") or {}
print(r.get("ok", None))
')"
      if [[ "$ok_flag" != "True" && "$ok_flag" != "true" ]]; then
        err="$(echo "$job_json" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
r=(d.get("payload") or {}).get("result") or {}
print(r.get("error") or d.get("last_error") or "")
')"
        if [[ -n "$err" ]]; then
          fail "${label} completed but result.ok is not true (ok=$ok_flag, error=$err)"
        fi
        fail "${label} completed but result.ok is not true (ok=$ok_flag)"
      fi
      return 0
    fi

    local now
    now="$(date +%s)"
    if (( now - start >= timeout_s )); then
      fail "${label} timed out after ${timeout_s}s (status=$status)"
    fi
    sleep "$poll_s"
  done
}

echo "=============================================="
echo "CAD Dedup Vision Verification (S3)"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "DB_URL: $DB_URL"
echo "S3_ENDPOINT_URL: $S3_ENDPOINT_URL"
echo "DEDUP_BASE_URL: $DEDUP_BASE_URL"
echo "USE_DOCKER_WORKER: $USE_DOCKER_WORKER_ENABLED (raw=$USE_DOCKER_WORKER)"
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

if [[ "$USE_DOCKER_WORKER_ENABLED" == "true" ]]; then
  echo ""
  echo "==> Preflight: Docker worker container (best-effort)"
  if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' --filter 'label=com.docker.compose.service=worker' --filter 'status=running' | grep -q .; then
      ok "Docker worker container is running"
    else
      echo "WARN: USE_DOCKER_WORKER=1 but no running compose worker container found (label com.docker.compose.service=worker)." >&2
      echo "WARN: The script will wait for jobs to be processed by an external worker; start the worker if it times out." >&2
    fi
  else
    echo "WARN: docker not found; USE_DOCKER_WORKER=1 will just wait for jobs to be processed by an external worker." >&2
  fi
fi

if [[ "$STORAGE_TYPE_ENV" != "s3" ]]; then
  fail "This script expects S3 storage. Set YUANTUS_STORAGE_TYPE=s3 (got: $STORAGE_TYPE_ENV)"
fi

# -----------------------------------------------------------------------------
# 1) Setup: Seed identity and meta
# -----------------------------------------------------------------------------
echo ""
echo "==> Seed identity (admin user)"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
ok "Identity seeded"

echo ""
echo "==> Seed meta schema"
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Meta schema seeded"

# -----------------------------------------------------------------------------
# 2) Login
# -----------------------------------------------------------------------------
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
# 3) Create a lenient dedup rule for 2D drawings (to make the verify stable)
# -----------------------------------------------------------------------------
echo ""
echo "==> Create dedup rule (2d, lenient thresholds)"
RULE_NAME="verify-dedup-vision-$(date +%s)"
RULE_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/dedup/rules" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{
      \"name\": \"${RULE_NAME}\",
      \"description\": \"Verification rule (auto-generated by scripts/verify_cad_dedup_vision_s3.sh)\",
      \"document_type\": \"2d\",
      \"phash_threshold\": 64,
      \"feature_threshold\": 0.0,
      \"combined_threshold\": 0.0,
      \"detection_mode\": \"fast\",
      \"priority\": 0,
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
# 4) Create two similar PNG files (different bytes, visually almost identical)
# -----------------------------------------------------------------------------
echo ""
echo "==> Create test PNG pair"
BASE_PNG="/tmp/yuantus_dedup_base.png"
QUERY_PNG="/tmp/yuantus_dedup_query.png"

"$PY" - << 'PY'
import random
import struct
import time
import zlib
from pathlib import Path

def _chunk(tag: bytes, payload: bytes) -> bytes:
    length = struct.pack(">I", len(payload))
    crc = struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    return length + tag + payload + crc

def write_png(path: str, *, width: int, height: int, seed: int, tweak: bool) -> None:
    width = int(width)
    height = int(height)
    # RGB, 8-bit, no interlace.
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    # Build raw scanlines: filter=0 + RGB bytes.
    # Use a seed-dependent block pattern so each run generates a meaningfully different image.
    # Keep baseline/query nearly identical (single-pixel tweak) to ensure the dedup result is deterministic.
    seed = int(seed)
    block = 16
    blocks_w = max(1, (width + block - 1) // block)
    blocks_h = max(1, (height + block - 1) // block)
    rng = random.Random(seed)
    grid = [[rng.getrandbits(1) for _ in range(blocks_w)] for __ in range(blocks_h)]
    rows = []
    for y in range(height):
        row = bytearray()
        row.append(0)  # filter
        for x in range(width):
            by = y // block
            bx = x // block
            v = 40 if grid[by][bx] == 0 else 220
            # Ensure query bytes differ from baseline without changing the overall pattern.
            if tweak and x == 0 and y == 0:
                v = (v + 1) % 256
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
write_png("/tmp/yuantus_dedup_base.png", width=256, height=256, seed=seed, tweak=False)
write_png("/tmp/yuantus_dedup_query.png", width=256, height=256, seed=seed, tweak=True)
PY

if [[ ! -s "$BASE_PNG" || ! -s "$QUERY_PNG" ]]; then
  fail "PNG generation failed"
fi
ok "Created PNG pair: $BASE_PNG, $QUERY_PNG"

# -----------------------------------------------------------------------------
# 5) Upload baseline PNG and index into Dedup Vision via cad_dedup_vision job
# -----------------------------------------------------------------------------
echo ""
echo "==> Upload baseline PNG via /cad/import (dedup_index=true)"
IMPORT_BASE_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$BASE_PNG;filename=verify_dedup_base.png" \
    -F 'create_preview_job=false' \
    -F 'create_geometry_job=false' \
    -F 'create_dedup_job=true' \
    -F 'dedup_mode=fast' \
    -F 'dedup_index=true' \
    -F 'create_ml_job=false'
)"

BASE_FILE_ID="$(
  echo "$IMPORT_BASE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id","") or "")'
)"
if [[ -z "$BASE_FILE_ID" ]]; then
  echo "Import response: $IMPORT_BASE_RESP" >&2
  fail "Could not get baseline file_id from import response"
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
  echo "Import response: $IMPORT_BASE_RESP" >&2
  fail "Could not get baseline cad_dedup_vision job id"
fi
echo "Baseline dedup job ID: $BASE_JOB_ID"

# -----------------------------------------------------------------------------
# 6) Process jobs
# -----------------------------------------------------------------------------
echo ""
echo "==> Wait for baseline job to complete"
wait_for_job_completed "$BASE_JOB_ID" "Baseline dedup job" 180
ok "Baseline job completed"

# -----------------------------------------------------------------------------
# 7) Verify baseline cad_dedup payload is persisted and readable
# -----------------------------------------------------------------------------
echo ""
echo "==> Verify baseline /file/{id}/cad_dedup"
BASE_META="$(
  # shellcheck disable=SC2086
  $CURL "$API/file/$BASE_FILE_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
BASE_CAD_DEDUP_URL="$(
  echo "$BASE_META" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("cad_dedup_url","") or "")'
)"
if [[ -z "$BASE_CAD_DEDUP_URL" ]]; then
  echo "File meta: $BASE_META" >&2
  fail "Baseline cad_dedup_url not set"
fi
ok "Baseline cad_dedup_url set: $BASE_CAD_DEDUP_URL"

BASE_DEDUP_PAYLOAD="$(
  # shellcheck disable=SC2086
  $CURL_FOLLOW "$BASE_URL$BASE_CAD_DEDUP_URL" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
echo "$BASE_DEDUP_PAYLOAD" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
assert d.get("kind") == "cad_dedup", d.keys()
search=d.get("search") or {}
assert search.get("success") is True, search
indexed=d.get("indexed") or {}
assert indexed.get("success") is True, indexed
print("ok")
' >/dev/null
ok "Baseline cad_dedup payload readable (search+index success)"

BASE_FILE_HASH="$(echo "$BASE_DEDUP_PAYLOAD" | "$PY" -c '
import sys,json
d=json.load(sys.stdin)
indexed=d.get("indexed") or {}
print(indexed.get("file_hash") or "")
')"
if [[ -z "$BASE_FILE_HASH" ]]; then
  echo "Baseline cad_dedup payload: $BASE_DEDUP_PAYLOAD" >&2
  fail "Baseline indexed.file_hash missing"
fi
ok "Baseline indexed file_hash: $BASE_FILE_HASH"

# -----------------------------------------------------------------------------
# 8) Upload query PNG and search for baseline
# -----------------------------------------------------------------------------
echo ""
echo "==> Upload query PNG via /cad/import (dedup_index=false)"
IMPORT_QUERY_RESP="$(
  # shellcheck disable=SC2086
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$QUERY_PNG;filename=verify_dedup_query.png" \
    -F 'create_preview_job=false' \
    -F 'create_geometry_job=false' \
    -F 'create_dedup_job=true' \
    -F 'dedup_mode=fast' \
    -F 'dedup_index=false' \
    -F 'create_ml_job=false'
)"

QUERY_FILE_ID="$(
  echo "$IMPORT_QUERY_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id","") or "")'
)"
if [[ -z "$QUERY_FILE_ID" ]]; then
  echo "Import response: $IMPORT_QUERY_RESP" >&2
  fail "Could not get query file_id from import response"
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
  echo "Import response: $IMPORT_QUERY_RESP" >&2
  fail "Could not get query cad_dedup_vision job id"
fi
echo "Query dedup job ID: $QUERY_JOB_ID"

echo ""
echo "==> Wait for query job to complete"
wait_for_job_completed "$QUERY_JOB_ID" "Query dedup job" 180
ok "Query job completed"

echo ""
echo "==> Verify query /file/{id}/cad_dedup includes baseline match"
QUERY_META="$(
  # shellcheck disable=SC2086
  $CURL "$API/file/$QUERY_FILE_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
QUERY_CAD_DEDUP_URL="$(
  echo "$QUERY_META" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("cad_dedup_url","") or "")'
)"
if [[ -z "$QUERY_CAD_DEDUP_URL" ]]; then
  echo "File meta: $QUERY_META" >&2
  fail "Query cad_dedup_url not set"
fi
ok "Query cad_dedup_url set: $QUERY_CAD_DEDUP_URL"

QUERY_DEDUP_PAYLOAD="$(
  # shellcheck disable=SC2086
  $CURL_FOLLOW "$BASE_URL$QUERY_CAD_DEDUP_URL" "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
echo "$QUERY_DEDUP_PAYLOAD" | EXPECTED_FILE_HASH="$BASE_FILE_HASH" "$PY" -c '
import os
import sys,json
d=json.load(sys.stdin)
search=d.get("search") or {}
assert search.get("success") is True, search
total=int(search.get("total_matches") or 0)

entries=[]

results=search.get("results")
if isinstance(results, list):
    entries.extend(results)

duplicates=search.get("duplicates")
if isinstance(duplicates, list):
    entries.extend(duplicates)

similar=search.get("similar")
if isinstance(similar, list):
    entries.extend(similar)

assert total >= 1 and entries, {"total_matches": total, "entries_len": len(entries), "search_keys": sorted(search.keys())}

expected_hash = os.environ.get("EXPECTED_FILE_HASH") or ""
assert expected_hash, "Missing EXPECTED_FILE_HASH env"
matched = [e for e in entries if isinstance(e, dict) and (e.get("file_hash") == expected_hash)]
assert matched, {"expected_file_hash": expected_hash, "entries_len": len(entries), "sample_names": [(e or {}).get("file_name") for e in entries[:5] if isinstance(e, dict)]}

names=[(e or {}).get("file_name") for e in matched if isinstance(e, dict)]
assert "verify_dedup_base.png" in names, names
print("ok")
' >/dev/null
ok "Query search returned baseline match"

echo ""
echo "ALL CHECKS PASSED"
