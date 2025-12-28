#!/usr/bin/env bash
# =============================================================================
# Backup/Restore Verification Script
# Validates backup artifacts and restores into isolated targets.
# =============================================================================
set -euo pipefail

PROJECT="${PROJECT:-yuantusplm}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/yuantus_backup_verify_$(date +%s)}"
PG_DATABASE_PREFIX="${PG_DATABASE_PREFIX:-yuantus}"
PG_USER="${PG_USER:-yuantus}"
PG_PASSWORD="${PG_PASSWORD:-yuantus}"
MINIO_BUCKET="${MINIO_BUCKET:-yuantus}"
RESTORE_BUCKET="${RESTORE_BUCKET:-yuantus-restore-test-$(date +%s)}"
RESTORE_DB_SUFFIX="${RESTORE_DB_SUFFIX:-_restore_$(date +%s)}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

echo "=============================================="
echo "Backup/Restore Verification"
echo "PROJECT: $PROJECT"
echo "BACKUP_DIR: $BACKUP_DIR"
echo "RESTORE_DB_SUFFIX: $RESTORE_DB_SUFFIX"
echo "RESTORE_BUCKET: $RESTORE_BUCKET"
echo "=============================================="

export PROJECT BACKUP_DIR PG_DATABASE_PREFIX MINIO_BUCKET PG_USER PG_PASSWORD

echo ""
echo "==> Run backup"
bash scripts/backup_private.sh
ok "Backup completed"

if [[ ! -d "$BACKUP_DIR/postgres" ]]; then
  fail "Missing Postgres backup directory"
fi

shopt -s nullglob
DUMPS=("$BACKUP_DIR"/postgres/*.dump)
shopt -u nullglob
if [[ ${#DUMPS[@]} -eq 0 ]]; then
  fail "No Postgres dump files created"
fi
ok "Postgres dumps created: ${#DUMPS[@]}"

if [[ ! -d "$BACKUP_DIR/minio/$MINIO_BUCKET" ]]; then
  fail "Missing MinIO backup directory: $BACKUP_DIR/minio/$MINIO_BUCKET"
fi
ok "MinIO backup directory exists"

export RESTORE_BUCKET RESTORE_DB_SUFFIX

echo ""
echo "==> Run restore (isolated targets)"
CONFIRM=yes bash scripts/restore_private.sh
ok "Restore completed"

TARGET_DB="$(basename "${DUMPS[0]}" .dump)${RESTORE_DB_SUFFIX}"
EXISTS="$(
  docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
    psql -U "$PG_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'" | tr -d '[:space:]'
)"
if [[ "$EXISTS" != "1" ]]; then
  fail "Restored DB not found: $TARGET_DB"
fi
ok "Restored DB exists: $TARGET_DB"

scheme="http"
if [[ "${MINIO_ENDPOINT:-http://minio:9000}" == https://* ]]; then
  scheme="https"
fi
endpoint_host="${MINIO_ENDPOINT:-http://minio:9000}"
endpoint_host="${endpoint_host#*//}"
mc_host="${scheme}://${MINIO_ACCESS_KEY:-minioadmin}:${MINIO_SECRET_KEY:-minioadmin}@${endpoint_host}"

if ! docker run --rm --network "${PROJECT}_default" \
  -e MC_HOST_minio="$mc_host" \
  -v "$BACKUP_DIR/minio":/backup \
  "${MC_IMAGE:-minio/mc:latest}" \
  ls "minio/$RESTORE_BUCKET" >/dev/null; then
  fail "Restored bucket not accessible: $RESTORE_BUCKET"
fi
ok "Restored bucket accessible: $RESTORE_BUCKET"

echo ""
echo "=============================================="
echo "Backup/Restore Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
