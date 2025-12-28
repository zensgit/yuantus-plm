#!/usr/bin/env bash
# =============================================================================
# Multi-tenant Postgres bootstrap
# Creates tenant/org databases for db-per-tenant-org verification.
# =============================================================================
set -euo pipefail

PROJECT="${PROJECT:-yuantusplm}"
DB_PREFIX="${DB_PREFIX:-yuantus_mt_pg__}"
IDENTITY_DB="${IDENTITY_DB:-yuantus_identity_mt_pg}"
TENANTS="${TENANTS:-tenant-1,tenant-2}"
ORGS="${ORGS:-org-1,org-2}"
RESET="${RESET:-0}"

IFS=',' read -r -a TENANT_LIST <<< "$TENANTS"
IFS=',' read -r -a ORG_LIST <<< "$ORGS"

create_db() {
  local db="$1"
  local exists
  exists="$(
    docker compose -p "$PROJECT" exec -T postgres \
      psql -U yuantus -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${db}'" \
      | tr -d '[:space:]'
  )"
  if [[ "$exists" != "1" ]]; then
    echo "Creating database: $db"
    docker compose -p "$PROJECT" exec -T postgres createdb -U yuantus "$db"
  else
    echo "Database exists: $db"
  fi
}

drop_db() {
  local db="$1"
  docker compose -p "$PROJECT" exec -T postgres \
    dropdb -U yuantus --if-exists --force "$db"
}

if [[ "$RESET" == "1" || "$RESET" == "true" ]]; then
  echo "Reset enabled: dropping tenant/org databases (destructive)"
  drop_db "$IDENTITY_DB"
  for tenant in "${TENANT_LIST[@]}"; do
    for org in "${ORG_LIST[@]}"; do
      drop_db "${DB_PREFIX}${tenant}__${org}"
    done
  done
fi

create_db "$IDENTITY_DB"
for tenant in "${TENANT_LIST[@]}"; do
  for org in "${ORG_LIST[@]}"; do
    create_db "${DB_PREFIX}${tenant}__${org}"
  done
done

echo ""
echo "Bootstrap complete."
echo "DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/${DB_PREFIX}{tenant_id}__{org_id}"
