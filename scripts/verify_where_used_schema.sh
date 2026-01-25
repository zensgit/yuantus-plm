#!/usr/bin/env bash
# =============================================================================
# Where-Used Line Schema Verification
# Validates schema metadata for BOM where-used line fields.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

if [[ "${LOCAL_TESTCLIENT:-0}" == "1" ]]; then
  BASE_URL="$BASE_URL" TENANT="$TENANT" ORG="$ORG" CLI="$CLI" PY="$PY" "$PY" - <<'PY'
import os
import random
import subprocess
import time

from fastapi.testclient import TestClient

from yuantus.api.app import app

tenant = os.environ["TENANT"]
org = os.environ["ORG"]
cli = os.environ["CLI"]

def run_cli(*args: str) -> None:
    subprocess.run([cli, *args], check=True)

ts = int(time.time())
admin_uid = int(os.environ.get("ADMIN_UID") or random.randint(600000, 950000))
username = f"admin-{ts}"
run_cli("seed-identity", "--tenant", tenant, "--org", org, "--username", username,
        "--password", "admin", "--user-id", str(admin_uid), "--roles", "admin")
run_cli("seed-meta", "--tenant", tenant, "--org", org)

client = TestClient(app)
headers = {"x-tenant-id": tenant, "x-org-id": org}

resp = client.post(
    "/api/v1/auth/login",
    json={
        "tenant_id": tenant,
        "username": username,
        "password": "admin",
        "org_id": org,
    },
)
resp.raise_for_status()

token = resp.json().get("access_token")
if not token:
    raise SystemExit("Admin login failed (no access_token)")

auth_headers = {**headers, "Authorization": f"Bearer {token}"}

resp = client.get("/api/v1/bom/where-used/schema", headers=auth_headers)
resp.raise_for_status()

schema = resp.json()
fields = {f.get("field") for f in schema.get("line_fields", [])}
expected_fields = {
    "quantity",
    "uom",
    "find_num",
    "refdes",
    "effectivity_from",
    "effectivity_to",
    "effectivities",
    "substitutes",
}
missing = expected_fields - fields
if missing:
    raise SystemExit(f"missing schema fields: {sorted(missing)}")

for entry in schema.get("line_fields", []):
    if not entry.get("severity"):
        raise SystemExit("missing severity in line field schema")
    if not entry.get("normalized"):
        raise SystemExit("missing normalized in line field schema")

print("ALL CHECKS PASSED")
PY
  exit 0
fi

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

printf "==============================================\n"
printf "Where-Used Line Schema Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 310000))}"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id "$ADMIN_UID" --roles admin >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null
ok "Seeded identity/meta"

printf "\n==> Login as admin\n"
ADMIN_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
ADMIN_AUTH=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

printf "\n==> Fetch where-used line schema\n"
SCHEMA_RESP="$(
  $CURL "$API/bom/where-used/schema" \
    "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"
SCHEMA_JSON="$SCHEMA_RESP" "$PY" - <<'PY'
import os
import json

data = json.loads(os.environ["SCHEMA_JSON"])
fields = {f.get("field") for f in data.get("line_fields", [])}
expected_fields = {
    "quantity",
    "uom",
    "find_num",
    "refdes",
    "effectivity_from",
    "effectivity_to",
    "effectivities",
    "substitutes",
}
missing_fields = expected_fields - fields
if missing_fields:
    raise SystemExit(f"missing schema fields: {sorted(missing_fields)}")

for entry in data.get("line_fields", []):
    if not entry.get("severity"):
        raise SystemExit("missing severity in line field schema")
    if not entry.get("normalized"):
        raise SystemExit("missing normalized in line field schema")

print("Where-used schema: OK")
PY
ok "Schema verified"

echo "ALL CHECKS PASSED"
