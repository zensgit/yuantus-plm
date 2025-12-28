#!/usr/bin/env bash
# =============================================================================
# Cleanup restore artifacts (Postgres DBs + MinIO buckets).
# Requires CONFIRM=yes to run.
# =============================================================================
set -euo pipefail

PROJECT="${PROJECT:-yuantusplm}"
CONFIRM="${CONFIRM:-}"

PG_USER="${PG_USER:-yuantus}"
PG_PASSWORD="${PG_PASSWORD:-yuantus}"
DB_LIST="${DB_LIST:-}"
DB_SUFFIX="${DB_SUFFIX:-}"
DB_PREFIX="${DB_PREFIX:-yuantus}"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
RESTORE_BUCKET="${RESTORE_BUCKET:-}"
BUCKETS="${BUCKETS:-}"

NETWORK="${NETWORK:-${PROJECT}_default}"
MC_IMAGE="${MC_IMAGE:-minio/mc:latest}"

SKIP_POSTGRES="${SKIP_POSTGRES:-}"
SKIP_MINIO="${SKIP_MINIO:-}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

if [[ "$CONFIRM" != "yes" ]]; then
  fail "Set CONFIRM=yes to proceed with cleanup"
fi

cleanup_dbs=()
if [[ -n "$DB_LIST" ]]; then
  IFS=',' read -r -a cleanup_dbs <<< "$DB_LIST"
elif [[ -n "$DB_SUFFIX" ]]; then
  mapfile -t cleanup_dbs < <(
    docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
      psql -U "$PG_USER" -d postgres -tAc \
      "SELECT datname FROM pg_database WHERE datistemplate = false AND datname NOT IN ('postgres') AND datname LIKE '${DB_PREFIX}%' ORDER BY datname;" \
      | awk -v suffix="$DB_SUFFIX" '$0 ~ suffix"$" {print $0}' \
      | xargs -n1 echo
  )
fi

if [[ -z "$SKIP_POSTGRES" ]]; then
  echo ""
  echo "==> Postgres cleanup"
  if [[ ${#cleanup_dbs[@]} -eq 0 ]]; then
    fail "No target DBs found (set DB_LIST or DB_SUFFIX)"
  fi
  for db in "${cleanup_dbs[@]}"; do
    db="$(echo "$db" | xargs)"
    [[ -z "$db" ]] && continue
    echo "Dropping DB: $db"
    docker compose -p "$PROJECT" exec -T -e PGPASSWORD="$PG_PASSWORD" postgres \
      dropdb -U "$PG_USER" --if-exists --force "$db"
    ok "Dropped $db"
  done
else
  echo ""
  echo "SKIP: Postgres cleanup"
fi

bucket_targets=()
if [[ -n "$RESTORE_BUCKET" ]]; then
  bucket_targets+=("$RESTORE_BUCKET")
fi
if [[ -n "$BUCKETS" ]]; then
  IFS=',' read -r -a bucket_targets <<< "$BUCKETS"
fi

if [[ -z "$SKIP_MINIO" ]]; then
  echo ""
  echo "==> MinIO cleanup"
  if [[ ${#bucket_targets[@]} -eq 0 ]]; then
    fail "No bucket targets provided (set RESTORE_BUCKET or BUCKETS)"
  fi

  scheme="http"
  if [[ "$MINIO_ENDPOINT" == https://* ]]; then
    scheme="https"
  fi
  endpoint_host="${MINIO_ENDPOINT#*//}"
  mc_host="${scheme}://${MINIO_ACCESS_KEY}:${MINIO_SECRET_KEY}@${endpoint_host}"

  for bucket in "${bucket_targets[@]}"; do
    bucket="$(echo "$bucket" | xargs)"
    [[ -z "$bucket" ]] && continue
    echo "Removing bucket: $bucket"
    docker run --rm \
      --network "$NETWORK" \
      -e MC_HOST_minio="$mc_host" \
      "$MC_IMAGE" \
      rb --force "minio/$bucket"
    ok "Removed bucket $bucket"
  done
else
  echo ""
  echo "SKIP: MinIO cleanup"
fi

echo ""
echo "Cleanup complete."
