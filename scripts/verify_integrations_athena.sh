#!/usr/bin/env bash
# =============================================================================
# Integrations Athena Verification Script
# Verifies /integrations/health with Athena auth isolation and service token.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CURL="${CURL:-curl -sS}"
PY="${PY:-.venv/bin/python}"

YUANTUS_TOKEN="${YUANTUS_TOKEN:-}"
ATHENA_TOKEN="${ATHENA_TOKEN:-}"
ATHENA_SERVICE_TOKEN="${ATHENA_SERVICE_TOKEN:-${YUANTUS_ATHENA_SERVICE_TOKEN:-}}"

if [[ ! -x "$PY" ]]; then
  PY="python3"
fi
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Missing python at $PY (set PY=...)" >&2
  exit 2
fi

HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")
AUTH_HEADERS=()
if [[ -n "$YUANTUS_TOKEN" ]]; then
  AUTH_HEADERS=(-H "Authorization: Bearer $YUANTUS_TOKEN")
fi

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

endpoint="$BASE_URL/api/v1/integrations/health"

if [[ -z "$ATHENA_TOKEN" && -z "$ATHENA_SERVICE_TOKEN" ]]; then
  echo "SKIP: Set ATHENA_TOKEN or ATHENA_SERVICE_TOKEN to run Athena validation." >&2
  exit 0
fi

if [[ -n "$ATHENA_TOKEN" ]]; then
  echo "==> Verify with X-Athena-Authorization"
  RESP="$($CURL "$endpoint" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H "X-Athena-Authorization: Bearer $ATHENA_TOKEN")"
  OK="$(RESP="$RESP" "$PY" - <<'PY'
import json, os, sys
raw = os.environ.get("RESP", "")
try:
    data = json.loads(raw)
except Exception:
    print("0"); sys.exit(0)
athena = (data.get("services") or {}).get("athena") or {}
print("1" if athena.get("ok") else "0")
PY
)"
  if [[ "$OK" != "1" ]]; then
    echo "Response: $RESP" >&2
    fail "Athena health failed with X-Athena-Authorization"
  fi
  ok "Athena health OK (X-Athena-Authorization)"
fi

if [[ -n "$ATHENA_SERVICE_TOKEN" ]]; then
  echo "==> Verify with YUANTUS_ATHENA_SERVICE_TOKEN"
  RESP="$($CURL "$endpoint" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
  OK="$(RESP="$RESP" "$PY" - <<'PY'
import json, os, sys
raw = os.environ.get("RESP", "")
try:
    data = json.loads(raw)
except Exception:
    print("0"); sys.exit(0)
athena = (data.get("services") or {}).get("athena") or {}
print("1" if athena.get("ok") else "0")
PY
)"
  if [[ "$OK" != "1" ]]; then
    echo "Response: $RESP" >&2
    fail "Athena health failed with service token"
  fi
  ok "Athena health OK (service token)"
fi

echo "ALL CHECKS PASSED"
