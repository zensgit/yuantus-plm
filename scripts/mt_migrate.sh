#!/usr/bin/env bash
# =============================================================================
# Multi-tenant migration helper
# Runs Alembic migrations for identity DB and each tenant/org database.
# =============================================================================
set -euo pipefail

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
MODE="${MODE:-${YUANTUS_TENANCY_MODE:-single}}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"
TENANTS="${TENANTS:-tenant-1,tenant-2}"
ORGS="${ORGS:-org-1,org-2}"
ACTION="${ACTION:-upgrade}"
AUTO_STAMP="${AUTO_STAMP:-1}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

if [[ "$ACTION" != "upgrade" && "$ACTION" != "current" && "$ACTION" != "history" ]]; then
  echo "Unsupported ACTION: $ACTION (use upgrade|current|history)" >&2
  exit 2
fi

run_db() {
  local url="$1"
  if [[ -z "$url" ]]; then
    echo "Missing database URL" >&2
    exit 2
  fi
  echo "→ Migrating: $url"
  if [[ "$ACTION" == "upgrade" && "$AUTO_STAMP" == "1" ]]; then
    needs_stamp="$(
      DB_URL="$url" "$PY" - <<'PY'
import os
from sqlalchemy import create_engine, inspect

url = os.environ.get("DB_URL")
engine = create_engine(url)
inspector = inspect(engine)
tables = set(inspector.get_table_names())
if tables and "alembic_version" not in tables:
    print("1")
else:
    print("0")
PY
    )"
    if [[ "$needs_stamp" == "1" ]]; then
      echo "Existing tables without alembic_version; stamping head"
      YUANTUS_DATABASE_URL="$url" "$CLI" db stamp --revision head
      return
    fi
  fi
  if ! YUANTUS_DATABASE_URL="$url" "$CLI" db "$ACTION"; then
    if [[ "$ACTION" == "upgrade" && "$AUTO_STAMP" == "1" ]]; then
      echo "Upgrade failed, stamping head (AUTO_STAMP=1)"
      YUANTUS_DATABASE_URL="$url" "$CLI" db stamp --revision head
    else
      exit 1
    fi
  fi
}

render_template() {
  local template="$1"
  local tenant="$2"
  local org="$3"
  local out="${template//\{tenant_id\}/$tenant}"
  out="${out//\{org_id\}/$org}"
  echo "$out"
}

echo "=============================================="
echo "Multi-tenant migrations"
echo "MODE: $MODE"
echo "TENANTS: $TENANTS"
echo "ORGS: $ORGS"
echo "ACTION: $ACTION"
echo "=============================================="

if [[ -n "$IDENTITY_DB_URL" ]]; then
  echo ""
  echo "==> Identity DB"
  run_db "$IDENTITY_DB_URL"
fi

if [[ "$MODE" == "single" ]]; then
  echo ""
  echo "==> Main DB"
  run_db "$DB_URL"
  exit 0
fi

if [[ -z "$DB_URL_TEMPLATE" ]]; then
  echo "DB_URL_TEMPLATE is required for MODE=$MODE" >&2
  exit 2
fi

IFS=',' read -r -a TENANT_LIST <<< "$TENANTS"
IFS=',' read -r -a ORG_LIST <<< "$ORGS"

echo ""
echo "==> Tenant migrations"
for tenant in "${TENANT_LIST[@]}"; do
  tenant="$(echo "$tenant" | xargs)"
  if [[ -z "$tenant" ]]; then
    continue
  fi
  if [[ "$MODE" == "db-per-tenant" ]]; then
    db_url="$(render_template "$DB_URL_TEMPLATE" "$tenant" "default")"
    run_db "$db_url"
    continue
  fi
  for org in "${ORG_LIST[@]}"; do
    org="$(echo "$org" | xargs)"
    if [[ -z "$org" ]]; then
      continue
    fi
    db_url="$(render_template "$DB_URL_TEMPLATE" "$tenant" "$org")"
    run_db "$db_url"
  done
done

echo ""
echo "Migrations complete."
