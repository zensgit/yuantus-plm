#!/usr/bin/env bash
# =============================================================================
# Private delivery restore script (Postgres + MinIO).
# Restores from a backup directory created by scripts/backup_private.sh.
# =============================================================================
set -euo pipefail

PROJECT="${PROJECT:-yuantusplm}"
BACKUP_DIR="${BACKUP_DIR:-}"
CONFIRM="${CONFIRM:-}"

PG_USER="${PG_USER:-yuantus}"
PG_PASSWORD="${PG_PASSWORD:-yuantus}"
RESTORE_DB_SUFFIX="${RESTORE_DB_SUFFIX:-}"
RESTORE_DROP="${RESTORE_DROP:-}"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKET="${MINIO_BUCKET:-yuantus}"
RESTORE_BUCKET="${RESTORE_BUCKET:-}"

NETWORK="${NETWORK:-${PROJECT}_default}"
MC_IMAGE="${MC_IMAGE:-minio/mc:latest}"

SKIP_POSTGRES="${SKIP_POSTGRES:-}"
SKIP_MINIO="${SKIP_MINIO:-}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

if [[ -z "$BACKUP_DIR" ]]; then
  fail "BACKUP_DIR is required"
fi
if [[ ! -d "$BACKUP_DIR" ]]; then
  fail "Backup directory not found: $BACKUP_DIR"
fi
if [[ "$CONFIRM" != "yes" ]]; then
  fail "Set CONFIRM=yes to proceed with restore"
fi

if [[ -z "$SKIP_POSTGRES" ]]; then
  echo ""
  echo "==> Postgres restore"
  shopt -s nullglob
  dumps=("$BACKUP_DIR"/postgres/*.dump)
  shopt -u nullglob
  if [[ ${#dumps[@]} -eq 0 ]]; then
    fail "No dump files found in $BACKUP_DIR/postgres"
  fi

  for dump in "${dumps[@]}"; do
    base="$(basename "$dump" .dump)"
    target_db="${base}${RESTORE_DB_SUFFIX}"
    if [[ -z "$target_db" ]]; then
      fail "Invalid target DB name for $dump"
    fi

    if [[ -n "$RESTORE_DROP" ]]; then
      echo "Dropping DB (if exists): $target_db"
      docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
        dropdb -U "$PG_USER" --if-exists --force "$target_db"
    fi

    exists="$(
      docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
        psql -U "$PG_USER" -d postgres -tAc \
        "SELECT 1 FROM pg_database WHERE datname='${target_db}'" | tr -d '[:space:]'
    )"

    if [[ "$exists" != "1" ]]; then
      echo "Creating DB: $target_db"
      docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
        createdb -U "$PG_USER" "$target_db"
    fi

    echo "Restoring $dump -> $target_db"
    cat "$dump" | docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
      pg_restore -U "$PG_USER" -d "$target_db" --clean --if-exists
    ok "Restored $target_db"
  done
else
  echo ""
  echo "SKIP: Postgres restore"
fi

if [[ -z "$SKIP_MINIO" ]]; then
  echo ""
  echo "==> MinIO restore"
  source_bucket="$MINIO_BUCKET"
  target_bucket="${RESTORE_BUCKET:-$MINIO_BUCKET}"
  source_path="$BACKUP_DIR/minio/$source_bucket"

  if [[ ! -d "$source_path" ]]; then
    fail "MinIO backup path not found: $source_path"
  fi

  scheme="http"
  if [[ "$MINIO_ENDPOINT" == https://* ]]; then
    scheme="https"
  fi
  endpoint_host="${MINIO_ENDPOINT#*//}"
  mc_host="${scheme}://${MINIO_ACCESS_KEY}:${MINIO_SECRET_KEY}@${endpoint_host}"

  docker run --rm \
    --network "$NETWORK" \
    -e MC_HOST_minio="$mc_host" \
    -v "$BACKUP_DIR/minio":/backup \
    "$MC_IMAGE" \
    mb --ignore-existing "minio/$target_bucket"

  docker run --rm \
    --network "$NETWORK" \
    -e MC_HOST_minio="$mc_host" \
    -v "$BACKUP_DIR/minio":/backup \
    "$MC_IMAGE" \
    mirror --overwrite "/backup/$source_bucket" "minio/$target_bucket"
  ok "Restored bucket $target_bucket"
else
  echo ""
  echo "SKIP: MinIO restore"
fi

echo ""
echo "Restore complete from: $BACKUP_DIR"
