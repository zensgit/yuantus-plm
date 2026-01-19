#!/usr/bin/env bash
# =============================================================================
# Where-Used UI Verification
# Validates line fields + recursive metadata in where-used responses.
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
admin_uid = int(os.environ.get("ADMIN_UID") or random.randint(500000, 950000))
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

def create_part(item_number: str, name: str) -> str:
    resp = client.post(
        "/api/v1/aml/apply",
        headers=auth_headers,
        json={
            "type": "Part",
            "action": "add",
            "properties": {"item_number": item_number, "name": name},
        },
    )
    resp.raise_for_status()
    item_id = resp.json().get("id")
    if not item_id:
        raise SystemExit("Failed to create part")
    return item_id

grand_id = create_part(f"WU-G-{ts}", f"WU Grand {ts}")
parent_id = create_part(f"WU-P-{ts}", f"WU Parent {ts}")
child_id = create_part(f"WU-C-{ts}", f"WU Child {ts}")

resp = client.post(
    f"/api/v1/bom/{parent_id}/children",
    headers=auth_headers,
    json={"child_id": child_id, "quantity": 2, "uom": "EA", "find_num": "10"},
)
resp.raise_for_status()
rel_parent_id = resp.json().get("relationship_id")
if not rel_parent_id:
    raise SystemExit("Failed to add parent->child")

resp = client.post(
    f"/api/v1/bom/{grand_id}/children",
    headers=auth_headers,
    json={"child_id": parent_id, "quantity": 1, "uom": "EA", "find_num": "20"},
)
resp.raise_for_status()
rel_grand_id = resp.json().get("relationship_id")
if not rel_grand_id:
    raise SystemExit("Failed to add grand->parent")

resp = client.get(
    f"/api/v1/bom/{child_id}/where-used",
    headers=auth_headers,
    params={"recursive": "true", "max_levels": "3"},
)
resp.raise_for_status()
data = resp.json()

if data.get("recursive") is not True:
    raise SystemExit("recursive flag missing or false")
if data.get("max_levels") != 3:
    raise SystemExit("max_levels mismatch")

parents = data.get("parents") or []
if len(parents) < 2:
    raise SystemExit("expected at least 2 where-used entries")

parent_ids = {p.get("parent", {}).get("id") for p in parents}
if parent_id not in parent_ids or grand_id not in parent_ids:
    raise SystemExit("missing expected parent/grand entries")

for entry in parents:
    line = entry.get("line") or {}
    line_norm = entry.get("line_normalized") or {}
    if "quantity" not in line or "quantity" not in line_norm:
        raise SystemExit("missing line quantity fields")
    child = entry.get("child") or {}
    rel = entry.get("relationship") or {}
    if child.get("id") != rel.get("related_id"):
        raise SystemExit("child mismatch in where-used entry")

print("ALL CHECKS PASSED")
PY
  exit 0
fi

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

printf "==============================================\n"
printf "Where-Used UI Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 500000))}"
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

TS="$(date +%s)"
GRAND_NUM="WU-G-$TS"
PARENT_NUM="WU-P-$TS"
CHILD_NUM="WU-C-$TS"

create_part() {
  local num="$1"
  local name="$2"
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$num\",\"name\":\"$name\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
}

printf "\n==> Create Parts\n"
GRAND_ID="$(create_part "$GRAND_NUM" "WU Grand $TS")"
PARENT_ID="$(create_part "$PARENT_NUM" "WU Parent $TS")"
CHILD_ID="$(create_part "$CHILD_NUM" "WU Child $TS")"

if [[ -z "$GRAND_ID" || -z "$PARENT_ID" || -z "$CHILD_ID" ]]; then
  fail "Failed to create where-used parts"
fi
ok "Created Parts: grand=$GRAND_ID parent=$PARENT_ID child=$CHILD_ID"

printf "\n==> Add BOM lines\n"
REL_PARENT="$(
  $CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"10\"}"
)"
REL_PARENT_ID="$(echo "$REL_PARENT" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_PARENT_ID" ]]; then
  echo "Response: $REL_PARENT"
  fail "Failed to add parent->child"
fi

REL_GRAND="$(
  $CURL -X POST "$API/bom/$GRAND_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$PARENT_ID\",\"quantity\":1,\"uom\":\"EA\",\"find_num\":\"20\"}"
)"
REL_GRAND_ID="$(echo "$REL_GRAND" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_GRAND_ID" ]]; then
  echo "Response: $REL_GRAND"
  fail "Failed to add grand->parent"
fi
ok "Added BOM lines: parent_rel=$REL_PARENT_ID grand_rel=$REL_GRAND_ID"

printf "\n==> Where-used (recursive)\n"
WHERE_USED_RESP="$(
  $CURL "$API/bom/$CHILD_ID/where-used?recursive=true&max_levels=3" "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

WHERE_USED_JSON="$WHERE_USED_RESP" CHILD_ID="$CHILD_ID" PARENT_ID="$PARENT_ID" GRAND_ID="$GRAND_ID" "$PY" - <<'PY'
import os
import json

data = json.loads(os.environ["WHERE_USED_JSON"])
parent_id = os.environ["PARENT_ID"]
grand_id = os.environ["GRAND_ID"]

if data.get("recursive") is not True:
    raise SystemExit("recursive flag missing or false")
if data.get("max_levels") != 3:
    raise SystemExit("max_levels mismatch")

parents = data.get("parents") or []
if len(parents) < 2:
    raise SystemExit("expected at least 2 where-used entries")

parent_ids = {p.get("parent", {}).get("id") for p in parents}
if parent_id not in parent_ids or grand_id not in parent_ids:
    raise SystemExit("missing expected parent/grand entries")

for entry in parents:
    line = entry.get("line") or {}
    line_norm = entry.get("line_normalized") or {}
    if "quantity" not in line or "quantity" not in line_norm:
        raise SystemExit("missing line quantity fields")
    child = entry.get("child") or {}
    rel = entry.get("relationship") or {}
    if child.get("id") != rel.get("related_id"):
        raise SystemExit("child mismatch in where-used entry")

print("Where-used UI payload: OK")
PY

printf "\n==============================================\n"
printf "Where-Used UI Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
