#!/usr/bin/env bash
# =============================================================================
# Multi-tenant Postgres bootstrap
# Creates tenant/org databases for db-per-tenant-org verification.
# =============================================================================
set -euo pipefail

# Historical default was "yuantusplm" (many docs use it), but compose projects
# are often started without "-p", in which case the project name is derived from
# the directory. Auto-detect a running project if the default doesn't match.
PROJECT="${PROJECT:-yuantusplm}"
DB_PREFIX="${DB_PREFIX:-yuantus_mt_pg__}"
IDENTITY_DB="${IDENTITY_DB:-yuantus_identity_mt_pg}"
TENANTS="${TENANTS:-tenant-1,tenant-2}"
ORGS="${ORGS:-org-1,org-2}"
RESET="${RESET:-0}"

IFS=',' read -r -a TENANT_LIST <<< "$TENANTS"
IFS=',' read -r -a ORG_LIST <<< "$ORGS"

COMPOSE_PROJECT_ARGS=(-p "$PROJECT")

detect_compose_project() {
  # First try explicit PROJECT (docs default). If nothing is running under that
  # project, fall back to the default compose project name (derived from cwd).
  local cid=""
  cid="$(docker compose "${COMPOSE_PROJECT_ARGS[@]}" ps -q postgres 2>/dev/null | head -n 1 || true)"
  if [[ -n "$cid" ]]; then
    return 0
  fi
  cid="$(docker compose ps -q postgres 2>/dev/null | head -n 1 || true)"
  if [[ -n "$cid" ]]; then
    COMPOSE_PROJECT_ARGS=()
    return 0
  fi
  echo "ERROR: Could not find a running 'postgres' container for docker compose." >&2
  echo "Hint: start it first: docker compose up -d postgres" >&2
  echo "If you used a custom project name, run: PROJECT=<name> $0" >&2
  exit 2
}

detect_compose_project

dc_postgres() {
  docker compose "${COMPOSE_PROJECT_ARGS[@]}" exec -T postgres "$@"
}

create_db() {
  local db="$1"
  local exists
  exists="$(
    dc_postgres psql -U yuantus -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${db}'" \
      | tr -d '[:space:]'
  )"
  if [[ "$exists" != "1" ]]; then
    echo "Creating database: $db"
    dc_postgres createdb -U yuantus "$db"
  else
    echo "Database exists: $db"
  fi
}

drop_db() {
  local db="$1"
  dc_postgres dropdb -U yuantus --if-exists --force "$db"
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
