#!/usr/bin/env bash
# =============================================================================
# Private delivery backup script (Postgres + MinIO).
# Creates a backup directory with DB dumps and object storage mirror.
# =============================================================================
set -euo pipefail

PROJECT="${PROJECT:-yuantusplm}"
BACKUP_DIR="${BACKUP_DIR:-./backups/yuantus_$(date +%Y%m%d_%H%M%S)}"

PG_USER="${PG_USER:-yuantus}"
PG_PASSWORD="${PG_PASSWORD:-yuantus}"
PG_DATABASES="${PG_DATABASES:-}"
PG_DATABASE_PREFIX="${PG_DATABASE_PREFIX:-yuantus}"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKET="${MINIO_BUCKET:-yuantus}"

NETWORK="${NETWORK:-${PROJECT}_default}"
MC_IMAGE="${MC_IMAGE:-minio/mc:latest}"

SKIP_POSTGRES="${SKIP_POSTGRES:-}"
SKIP_MINIO="${SKIP_MINIO:-}"
ARCHIVE="${ARCHIVE:-}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

mkdir -p "$BACKUP_DIR/postgres" "$BACKUP_DIR/minio"

stamp_file="$BACKUP_DIR/backup_meta.txt"
{
  echo "timestamp=$(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "project=$PROJECT"
  echo "pg_user=$PG_USER"
  echo "pg_prefix=$PG_DATABASE_PREFIX"
  echo "minio_endpoint=$MINIO_ENDPOINT"
  echo "minio_bucket=$MINIO_BUCKET"
} > "$stamp_file"

if [[ -z "$SKIP_POSTGRES" ]]; then
  echo ""
  echo "==> Postgres backup"
  if [[ -n "$PG_DATABASES" ]]; then
    IFS=',' read -r -a DB_LIST <<< "$PG_DATABASES"
  else
    mapfile -t DB_LIST < <(
      docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
        psql -U "$PG_USER" -d postgres -tAc \
        "SELECT datname FROM pg_database WHERE datistemplate = false AND datname NOT IN ('postgres') AND datname LIKE '${PG_DATABASE_PREFIX}%' ORDER BY datname;" \
        | xargs -n1 echo
    )
  fi

  if [[ ${#DB_LIST[@]} -eq 0 ]]; then
    fail "No databases found to backup (prefix=$PG_DATABASE_PREFIX)"
  fi

  printf "%s\n" "${DB_LIST[@]}" > "$BACKUP_DIR/postgres/databases.txt"

  for db in "${DB_LIST[@]}"; do
    db="$(echo "$db" | xargs)"
    [[ -z "$db" ]] && continue
    dump_file="$BACKUP_DIR/postgres/${db}.dump"
    echo "Backing up DB: $db"
    docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
      pg_dump -U "$PG_USER" -Fc -d "$db" > "$dump_file"
    ok "Saved $dump_file"
  done
else
  echo ""
  echo "SKIP: Postgres backup"
fi

if [[ -z "$SKIP_MINIO" ]]; then
  echo ""
  echo "==> MinIO backup"
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
    mirror --overwrite "minio/$MINIO_BUCKET" "/backup/$MINIO_BUCKET"
  ok "Mirrored bucket $MINIO_BUCKET to $BACKUP_DIR/minio/$MINIO_BUCKET"
else
  echo ""
  echo "SKIP: MinIO backup"
fi

if [[ -n "$ARCHIVE" ]]; then
  echo ""
  echo "==> Archive"
  tarball="${BACKUP_DIR%/}.tar.gz"
  tar -czf "$tarball" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
  ok "Archived to $tarball"
fi

echo ""
echo "Backup complete: $BACKUP_DIR"
