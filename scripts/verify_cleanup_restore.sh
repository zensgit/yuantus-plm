#!/usr/bin/env bash
# =============================================================================
# Cleanup Verification Script
# Creates test DB + bucket, then removes them via cleanup_private_restore.sh.
# =============================================================================
set -euo pipefail

PROJECT="${PROJECT:-yuantusplm}"
TEST_SUFFIX="${TEST_SUFFIX:-$(date +%s)}"

PG_USER="${PG_USER:-yuantus}"
PG_PASSWORD="${PG_PASSWORD:-yuantus}"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"

DB_NAME="${DB_NAME:-yuantus_cleanup_test_${TEST_SUFFIX}}"
BUCKET_NAME="${BUCKET_NAME:-yuantus-cleanup-test-${TEST_SUFFIX}}"

NETWORK="${NETWORK:-${PROJECT}_default}"
MC_IMAGE="${MC_IMAGE:-minio/mc:latest}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

scheme="http"
if [[ "$MINIO_ENDPOINT" == https://* ]]; then
  scheme="https"
fi
endpoint_host="${MINIO_ENDPOINT#*//}"
mc_host="${scheme}://${MINIO_ACCESS_KEY}:${MINIO_SECRET_KEY}@${endpoint_host}"

echo "=============================================="
echo "Cleanup Verification"
echo "PROJECT: $PROJECT"
echo "DB_NAME: $DB_NAME"
echo "BUCKET_NAME: $BUCKET_NAME"
echo "=============================================="

echo ""
echo "==> Create test DB"
docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
  createdb -U "$PG_USER" "$DB_NAME"
ok "Created DB $DB_NAME"

exists="$(
  docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
    psql -U "$PG_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | tr -d '[:space:]'
)"
[[ "$exists" == "1" ]] || fail "DB not created: $DB_NAME"

echo ""
echo "==> Create test bucket"
TMP_FILE="/tmp/yuantus_cleanup_${TEST_SUFFIX}.txt"
echo "cleanup test" > "$TMP_FILE"

# Create bucket and upload a file
if ! docker run --rm --network "$NETWORK" \
  -e MC_HOST_minio="$mc_host" \
  -v /tmp:/backup \
  "$MC_IMAGE" \
  mb --ignore-existing "minio/$BUCKET_NAME" >/dev/null; then
  fail "Failed to create bucket"
fi

if ! docker run --rm --network "$NETWORK" \
  -e MC_HOST_minio="$mc_host" \
  -v /tmp:/backup \
  "$MC_IMAGE" \
  cp "/backup/$(basename "$TMP_FILE")" "minio/$BUCKET_NAME/$(basename "$TMP_FILE")" >/dev/null; then
  fail "Failed to upload test object"
fi
ok "Created bucket $BUCKET_NAME"

rm -f "$TMP_FILE"

echo ""
echo "==> Run cleanup"
CONFIRM=yes DB_LIST="$DB_NAME" RESTORE_BUCKET="$BUCKET_NAME" \
  bash scripts/cleanup_private_restore.sh
ok "Cleanup executed"

echo ""
echo "==> Verify DB removed"
exists_after="$(
  docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
    psql -U "$PG_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | tr -d '[:space:]'
)"
if [[ -n "$exists_after" ]]; then
  fail "DB still exists: $DB_NAME"
fi
ok "DB removed"

echo ""
echo "==> Verify bucket removed"
if docker run --rm --network "$NETWORK" \
  -e MC_HOST_minio="$mc_host" \
  "$MC_IMAGE" \
  ls "minio/$BUCKET_NAME" >/dev/null 2>&1; then
  fail "Bucket still exists: $BUCKET_NAME"
fi
ok "Bucket removed"

echo ""
echo "=============================================="
echo "Cleanup Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
