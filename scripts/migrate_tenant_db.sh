#!/usr/bin/env bash
set -euo pipefail

TENANT="${1:-${TENANT:-tenant-1}}"
ORG="${2:-${ORG:-org-1}}"
PY="${PY:-.venv/bin/python}"
ALEMBIC="${ALEMBIC:-.venv/bin/alembic}"

if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi
if [[ ! -x "$ALEMBIC" ]]; then
  echo "Missing Alembic at $ALEMBIC (set ALEMBIC=...)" >&2
  exit 2
fi

DB_URL="$(
  TENANT="$TENANT" ORG="$ORG" "$PY" - <<'PY'
import os
from yuantus.database import resolve_database_url

tenant = os.getenv("TENANT")
org = os.getenv("ORG")
print(resolve_database_url(tenant_id=tenant, org_id=org))
PY
)"

echo "Using DB URL: $DB_URL"
YUANTUS_DATABASE_URL="$DB_URL" "$ALEMBIC" upgrade head
