#!/usr/bin/env bash
# =============================================================================
# Audit Logs Verification Script
# Verifies /admin/audit returns recent logs when AUDIT_ENABLED=true.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
DB_URL="${DB_URL:-}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"
RETENTION_DAYS="${AUDIT_RETENTION_DAYS:-${YUANTUS_AUDIT_RETENTION_DAYS:-0}}"
RETENTION_MAX_ROWS="${AUDIT_RETENTION_MAX_ROWS:-${YUANTUS_AUDIT_RETENTION_MAX_ROWS:-0}}"
RETENTION_PRUNE_INTERVAL="${AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS:-${YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS:-0}}"
VERIFY_RETENTION="${VERIFY_RETENTION:-}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$DB_URL" || -n "$identity_url" ]]; then
    env \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

echo "=============================================="
echo "Audit Logs Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

AUDIT_ENABLED="$(
  $CURL "$API/health" "${HEADERS[@]}" \
    | "$PY" -c 'import sys,json;print(str(json.load(sys.stdin).get("audit_enabled","")).lower())'
)"
if [[ "$AUDIT_ENABLED" != "true" ]]; then
  echo "SKIP: audit_enabled=false (set YUANTUS_AUDIT_ENABLED=true)"
  exit 0
fi

echo ""
echo "==> Seed identity"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
ok "Seeded identity"

echo ""
echo "==> Login as admin"
TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH=(-H "Authorization: Bearer $TOKEN")
ok "Admin login"

echo ""
echo "==> Trigger audit log (health request)"
$CURL "$API/health" "${HEADERS[@]}" "${AUTH[@]}" >/dev/null
ok "Health request logged"

echo ""
echo "==> Fetch audit logs"
RESP="$($CURL "$API/admin/audit?limit=20&path=/api/v1/health" "${HEADERS[@]}" "${AUTH[@]}")"

RESP_JSON="$RESP" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /admin/audit")

data = json.loads(raw)
items = data.get("items") or []
if not items:
    raise SystemExit("No audit logs returned")

if not any("/api/v1/health" in (item.get("path") or "") for item in items):
    raise SystemExit("Expected /api/v1/health log entry")

print("Audit logs: OK")
PY
ok "Audit logs verified"

if [[ -z "$VERIFY_RETENTION" ]]; then
  if [[ "$RETENTION_DAYS" -gt 0 || "$RETENTION_MAX_ROWS" -gt 0 ]]; then
    VERIFY_RETENTION=1
  else
    VERIFY_RETENTION=0
  fi
fi

if [[ "$VERIFY_RETENTION" == "1" ]]; then
  echo ""
  echo "==> Retention check"

  TARGET_COUNT=10
  if [[ "$RETENTION_MAX_ROWS" -gt 0 ]]; then
    TARGET_COUNT="$RETENTION_MAX_ROWS"
  fi

  for _i in $(seq 1 $((TARGET_COUNT + 3))); do
    $CURL "$API/health" "${HEADERS[@]}" "${AUTH[@]}" >/dev/null
  done

  OLD_LOG_ID=""
  if [[ "$RETENTION_DAYS" -gt 0 && -n "$IDENTITY_DB_URL" ]]; then
    OLD_LOG_ID="$(
      TENANT="$TENANT" RETENTION_DAYS="$RETENTION_DAYS" IDENTITY_DB_URL="$IDENTITY_DB_URL" \
        "$PY" - <<'PY'
import datetime
import os
from sqlalchemy import create_engine, text

url = os.environ.get("IDENTITY_DB_URL")
tenant = os.environ.get("TENANT")
days = int(os.environ.get("RETENTION_DAYS", "0"))
if not url or not tenant or days <= 0:
    print("")
    raise SystemExit(0)

cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days + 1)
engine = create_engine(url)
with engine.begin() as conn:
    row = conn.execute(
        text("SELECT id FROM audit_logs WHERE tenant_id=:tenant ORDER BY created_at DESC LIMIT 1"),
        {"tenant": tenant},
    ).fetchone()
    if not row:
        print("")
        raise SystemExit(0)
    conn.execute(
        text("UPDATE audit_logs SET created_at=:cutoff WHERE id=:id"),
        {"cutoff": cutoff, "id": row[0]},
    )
    print(row[0])
PY
    )"
  fi

  if [[ "$RETENTION_PRUNE_INTERVAL" -gt 0 ]]; then
    sleep "$RETENTION_PRUNE_INTERVAL"
  fi

  $CURL "$API/health" "${HEADERS[@]}" "${AUTH[@]}" >/dev/null

  RET_RESP="$($CURL "$API/admin/audit?limit=200" "${HEADERS[@]}" "${AUTH[@]}")"
  RET_RESP_JSON="$RET_RESP" RETENTION_MAX_ROWS="$RETENTION_MAX_ROWS" OLD_LOG_ID="$OLD_LOG_ID" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("RET_RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /admin/audit")

data = json.loads(raw)
items = data.get("items") or []
total = int(data.get("total") or 0)
max_rows = int(os.environ.get("RETENTION_MAX_ROWS", "0"))
old_id = os.environ.get("OLD_LOG_ID") or ""

if max_rows > 0 and total > max_rows:
    raise SystemExit(f"Retention max rows exceeded: total={total} > {max_rows}")

if old_id:
    if any(item.get("id") == old_id for item in items):
        raise SystemExit("Retention days did not prune old log entry")

print("Audit retention: OK")
PY
  ok "Audit retention verified"
fi

echo ""
echo "=============================================="
echo "Audit Logs Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
