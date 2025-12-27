#!/usr/bin/env bash
# =============================================================================
# Ops Health Verification Script
# Verifies /health and /health/deps dependency checks.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
CHECK_EXTERNAL="${CHECK_EXTERNAL:-${YUANTUS_HEALTHCHECK_EXTERNAL:-}}"
CHECK_INTEGRATIONS="${CHECK_INTEGRATIONS:-}"
YUANTUS_AUTH_TOKEN="${YUANTUS_AUTH_TOKEN:-}"
YUANTUS_USERNAME="${YUANTUS_USERNAME:-admin}"
YUANTUS_PASSWORD="${YUANTUS_PASSWORD:-admin}"
ATHENA_AUTH_TOKEN="${ATHENA_AUTH_TOKEN:-${ATHENA_TOKEN:-}}"

if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

echo "=============================================="
echo "Ops Health Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> /health"
HEALTH_RESP="$($CURL "$API/health" "${HEADERS[@]}")"
HEALTH_RESP_JSON="$HEALTH_RESP" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("HEALTH_RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /health")
data = json.loads(raw)
if not data.get("ok"):
    raise SystemExit("health ok=false")
print("Health: OK")
PY
ok "/health ok"

echo ""
echo "==> /health/deps"
DEPS_RESP="$($CURL "$API/health/deps" "${HEADERS[@]}")"
DEPS_RESP_JSON="$DEPS_RESP" CHECK_EXTERNAL="$CHECK_EXTERNAL" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("DEPS_RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /health/deps")
data = json.loads(raw)
if not data.get("ok"):
    raise SystemExit("health/deps ok=false")
deps = data.get("deps") or {}
for key in ("db", "identity_db", "storage"):
    info = deps.get(key) or {}
    if not info.get("ok"):
        raise SystemExit(f"deps.{key} ok=false")

check_external = str(os.environ.get("CHECK_EXTERNAL", "")).lower() in {"1","true","yes"}
if check_external:
    external = data.get("external") or {}
    for name, info in external.items():
        if not info.get("configured"):
            continue
        ok = info.get("ok")
        if ok is not True:
            raise SystemExit(f"external.{name} ok=false")

print("Health deps: OK")
PY
ok "/health/deps ok"

if [[ "$(printf '%s' "$CHECK_INTEGRATIONS" | tr '[:upper:]' '[:lower:]')" =~ ^(1|true|yes)$ ]]; then
  echo ""
  echo "==> /integrations/health"
  if [[ -z "$YUANTUS_AUTH_TOKEN" ]]; then
    YUANTUS_AUTH_TOKEN="$(
      $CURL -X POST "$API/auth/login" \
        -H 'content-type: application/json' \
        -d "{\"tenant_id\":\"$TENANT\",\"username\":\"$YUANTUS_USERNAME\",\"password\":\"$YUANTUS_PASSWORD\",\"org_id\":\"$ORG\"}" \
        | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
    )"
  fi
  if [[ -z "$YUANTUS_AUTH_TOKEN" ]]; then
    fail "Missing YUANTUS_AUTH_TOKEN (or valid YUANTUS_USERNAME/YUANTUS_PASSWORD)"
  fi

  AUTH_HEADERS=(-H "Authorization: Bearer $YUANTUS_AUTH_TOKEN")
  if [[ -n "$ATHENA_AUTH_TOKEN" ]]; then
    AUTH_HEADERS+=(-H "X-Athena-Authorization: Bearer $ATHENA_AUTH_TOKEN")
  fi

  INTEGRATIONS_RESP="$($CURL "$API/integrations/health" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
  INTEGRATIONS_RESP_JSON="$INTEGRATIONS_RESP" ATHENA_EXPECTED="$ATHENA_AUTH_TOKEN" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("INTEGRATIONS_RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /integrations/health")
data = json.loads(raw)
services = data.get("services") or {}
athena = services.get("athena") or {}

if os.environ.get("ATHENA_EXPECTED"):
    if not athena.get("ok"):
        status = athena.get("status_code")
        raise SystemExit(f"athena ok=false (status_code={status})")

print("Integrations health: OK")
PY
  ok "/integrations/health ok"
fi

echo ""
echo "=============================================="
echo "Ops Health Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
