#!/usr/bin/env bash
# =============================================================================
# Plugin Framework Verification
# Verifies: plugin discovery, health/status, and capabilities/schema exposure.
# =============================================================================
set -euo pipefail

BASE="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"
TENANCY_MODE="${TENANCY_MODE:-${YUANTUS_TENANCY_MODE:-}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

CLI_ENV=()
if [[ -n "$DB_URL" ]]; then
  CLI_ENV+=("YUANTUS_DATABASE_URL=$DB_URL")
fi
if [[ -n "$IDENTITY_DB_URL" ]]; then
  CLI_ENV+=("YUANTUS_IDENTITY_DATABASE_URL=$IDENTITY_DB_URL")
fi
if [[ -n "$TENANCY_MODE" ]]; then
  CLI_ENV+=("YUANTUS_TENANCY_MODE=$TENANCY_MODE")
fi
if [[ -n "$DB_URL_TEMPLATE" ]]; then
  CLI_ENV+=("YUANTUS_DATABASE_URL_TEMPLATE=$DB_URL_TEMPLATE")
fi

run_cli() {
  if [[ ${#CLI_ENV[@]} -gt 0 ]]; then
    env "${CLI_ENV[@]}" "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

printf "==============================================\n"
printf "Plugin Framework Verification\n"
printf "BASE_URL: %s\n" "$BASE"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity\n"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null

printf "\n==> Login\n"
TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"

printf "\n==> List plugins\n"
PLUGINS_JSON="$(
  curl -s "$BASE/api/v1/plugins" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"
"$PY" - <<PY
import json,sys

payload=json.loads("""${PLUGINS_JSON}""")
assert payload.get("ok") is True, payload
plugins=payload.get("plugins", [])
if not plugins:
    raise SystemExit("FAIL: no plugins discovered")
print(f"Plugins discovered: {len(plugins)}")
# prefer demo plugin if present
plugin_id = "yuantus-demo"
ids = [p.get("id") for p in plugins]
if plugin_id not in ids:
    plugin_id = ids[0]
status = next(p.get("status") for p in plugins if p.get("id") == plugin_id)
if status not in ("active", "loaded"):
    raise SystemExit(f"FAIL: plugin {plugin_id} status={status}")
print(f"Plugin health OK: {plugin_id} status={status}")
print(plugin_id)
PY

PLUGIN_ID="$(${PY} - <<PY
import json
payload=json.loads("""${PLUGINS_JSON}""")
ids=[p.get("id") for p in payload.get("plugins", [])]
print("yuantus-demo" if "yuantus-demo" in ids else ids[0])
PY
)"

printf "\n==> Plugin config (schema/capabilities)\n"
curl -s "$BASE/api/v1/plugins/${PLUGIN_ID}/config" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok") is True;assert "schema" in d and "capabilities" in d;print("Config OK")'

printf "\n==> Plugin ping (demo)\n"
if [[ "$PLUGIN_ID" == "yuantus-demo" ]]; then
  curl -s "$BASE/api/v1/plugins/demo/ping" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok") is True;print("Ping OK")'
else
  printf "SKIP: demo ping (plugin_id=%s)\n" "$PLUGIN_ID"
fi

printf "\n==============================================\n"
printf "Plugin Framework Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
