#!/usr/bin/env bash
# =============================================================================
# Document + ECO UI Summary Verification
# Validates document lifecycle summary + ECO approval summary on product detail.
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
admin_uid = int(os.environ.get("ADMIN_UID") or random.randint(600000, 980000))
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

def ensure_item_type(type_id: str, payload: dict) -> None:
    resp = client.get(f"/api/v1/meta/item-types/{type_id}", headers=auth_headers)
    if resp.status_code == 200:
        return
    resp = client.post("/api/v1/meta/item-types", headers=auth_headers, json=payload)
    if resp.status_code not in (200, 409):
        raise SystemExit(f"Failed to ensure ItemType {type_id}")

ensure_item_type(
    "Document",
    {"id": "Document", "label": "Document", "is_relationship": False, "is_versionable": True},
)
ensure_item_type(
    "Document Part",
    {
        "id": "Document Part",
        "label": "Document Part",
        "is_relationship": True,
        "is_versionable": False,
        "source_item_type_id": "Part",
        "related_item_type_id": "Document",
    },
)

part_num = f"DOCUI-P-{ts}"
doc_num = f"DOCUI-D-{ts}"

resp = client.post(
    "/api/v1/aml/apply",
    headers=auth_headers,
    json={
        "type": "Part",
        "action": "add",
        "properties": {"item_number": part_num, "name": "Doc UI Product"},
    },
)
resp.raise_for_status()
part_id = resp.json().get("id")

resp = client.post(
    "/api/v1/aml/apply",
    headers=auth_headers,
    json={
        "type": "Document",
        "action": "add",
        "properties": {"item_number": doc_num, "doc_number": doc_num, "name": "Doc UI Doc"},
    },
)
resp.raise_for_status()
doc_id = resp.json().get("id")

if not part_id or not doc_id:
    raise SystemExit("Failed to create Part/Document")

resp = client.post(
    "/api/v1/rpc/",
    headers=auth_headers,
    json={"model": "Relationship", "method": "add", "args": [part_id, "Document Part", doc_id, {}]},
)
resp.raise_for_status()
if resp.json().get("result", {}).get("status") != "success":
    raise SystemExit("Failed to create Document Part relationship")

resp = client.post(
    "/api/v1/eco/stages",
    headers=auth_headers,
    json={
        "name": f"DOCUI-STAGE-{ts}",
        "sequence": 90,
        "approval_type": "mandatory",
        "approval_roles": ["admin"],
        "auto_progress": False,
        "is_blocking": False,
        "sla_hours": 0,
    },
)
resp.raise_for_status()
stage_id = resp.json().get("id")
if not stage_id:
    raise SystemExit("Failed to create ECO stage")

resp = client.post(
    "/api/v1/eco",
    headers=auth_headers,
    json={
        "name": f"DOCUI-ECO-{ts}",
        "eco_type": "bom",
        "product_id": part_id,
        "description": "doc ui summary",
    },
)
resp.raise_for_status()
eco_id = resp.json().get("id")
if not eco_id:
    raise SystemExit("Failed to create ECO")

resp = client.post(
    f"/api/v1/eco/{eco_id}/move-stage",
    headers=auth_headers,
    json={"stage_id": stage_id},
)
resp.raise_for_status()
if resp.json().get("stage_id") != stage_id:
    raise SystemExit("Failed to move ECO to stage")

resp = client.get(
    f"/api/v1/products/{part_id}",
    headers=auth_headers,
    params={
        "include_versions": "false",
        "include_files": "false",
        "include_document_summary": "true",
        "include_eco_summary": "true",
    },
)
resp.raise_for_status()
data = resp.json()

doc_summary = data.get("document_summary") or {}
eco_summary = data.get("eco_summary") or {}

if doc_summary.get("authorized") is False:
    raise SystemExit("document summary unauthorized")
if doc_summary.get("count", 0) < 1:
    raise SystemExit("expected document summary count >= 1")
doc_items = doc_summary.get("items") or []
if not doc_items:
    raise SystemExit("expected document summary items")

eco_count = eco_summary.get("count", 0)
if eco_summary.get("authorized") is False or eco_count < 1:
    raise SystemExit("expected eco summary count >= 1")

pending = eco_summary.get("pending_approvals") or {}
if pending.get("count", 0) < 1:
    raise SystemExit("expected pending approval count >= 1")
eco_items = eco_summary.get("items") or []
if not eco_items:
    raise SystemExit("expected eco summary items")

print("ALL CHECKS PASSED")
PY
  exit 0
fi

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

printf "==============================================\n"
printf "Docs + ECO UI Summary Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 600000))}"
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

ensure_item_type() {
  local type_id="$1"
  local payload="$2"
  local encoded
  encoded="$("$PY" -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$type_id")"
  local resp
  resp="$($CURL -w 'HTTPSTATUS:%{http_code}' "$API/meta/item-types/$encoded" "${HEADERS[@]}" "${ADMIN_AUTH[@]}")"
  local status="${resp##*HTTPSTATUS:}"
  if [[ "$status" == "200" ]]; then
    return 0
  fi
  resp="$($CURL -w 'HTTPSTATUS:%{http_code}' -X POST "$API/meta/item-types" \
    -H 'content-type: application/json' \
    "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -d "$payload")"
  status="${resp##*HTTPSTATUS:}"
  if [[ "$status" != "200" && "$status" != "409" ]]; then
    echo "Response: ${resp%HTTPSTATUS:*}" >&2
    fail "Failed to ensure ItemType $type_id"
  fi
}

printf "\n==> Ensure Document ItemTypes\n"
ensure_item_type "Document" "{\"id\":\"Document\",\"label\":\"Document\",\"is_relationship\":false,\"is_versionable\":true}"
ensure_item_type "Document Part" "{\"id\":\"Document Part\",\"label\":\"Document Part\",\"is_relationship\":true,\"is_versionable\":false,\"source_item_type_id\":\"Part\",\"related_item_type_id\":\"Document\"}"
ok "Document ItemTypes ensured"

TS="$(date +%s)"
PART_NUM="DOCUI-P-$TS"
DOC_NUM="DOCUI-D-$TS"

printf "\n==> Create Part and Document\n"
PART_RESP="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PART_NUM\",\"name\":\"Doc UI Product\"}}"
)"
PART_ID="$(echo "$PART_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
DOC_RESP="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Document\",\"action\":\"add\",\"properties\":{\"item_number\":\"$DOC_NUM\",\"doc_number\":\"$DOC_NUM\",\"name\":\"Doc UI Doc\"}}"
)"
DOC_ID="$(echo "$DOC_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$PART_ID" || -z "$DOC_ID" ]]; then
  echo "Part response: $PART_RESP" >&2
  echo "Doc response: $DOC_RESP" >&2
  fail "Failed to create Part/Document"
fi
ok "Created Part=$PART_ID Document=$DOC_ID"

printf "\n==> Link Document to Part\n"
REL_RESP="$(
  $CURL -X POST "$API/rpc/" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"model\":\"Relationship\",\"method\":\"add\",\"args\":[\"$PART_ID\",\"Document Part\",\"$DOC_ID\",{}]}"
)"
REL_STATUS="$(echo "$REL_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("result",{}).get("status",""))')"
if [[ "$REL_STATUS" != "success" ]]; then
  echo "Response: $REL_RESP" >&2
  fail "Failed to create Document Part relationship"
fi
ok "Created Document relation"

printf "\n==> Create ECO stage and ECO\n"
STAGE_RESP="$(
  $CURL -X POST "$API/eco/stages" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"DOCUI-STAGE-$TS\",\"sequence\":90,\"approval_type\":\"mandatory\",\"approval_roles\":[\"admin\"],\"auto_progress\":false,\"is_blocking\":false,\"sla_hours\":0}"
)"
STAGE_ID="$(echo "$STAGE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$STAGE_ID" ]]; then
  echo "Response: $STAGE_RESP" >&2
  fail "Failed to create ECO stage"
fi

ECO_RESP="$(
  $CURL -X POST "$API/eco" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"DOCUI-ECO-$TS\",\"eco_type\":\"bom\",\"product_id\":\"$PART_ID\",\"description\":\"doc ui summary\"}"
)"
ECO_ID="$(echo "$ECO_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$ECO_ID" ]]; then
  echo "Response: $ECO_RESP" >&2
  fail "Failed to create ECO"
fi

MOVE_RESP="$(
  $CURL -X POST "$API/eco/$ECO_ID/move-stage" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"stage_id\":\"$STAGE_ID\"}"
)"
MOVE_STAGE_ID="$(echo "$MOVE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("stage_id",""))')"
if [[ "$MOVE_STAGE_ID" != "$STAGE_ID" ]]; then
  echo "Response: $MOVE_RESP" >&2
  fail "Failed to move ECO to stage"
fi
ok "Created ECO=$ECO_ID stage=$STAGE_ID"

printf "\n==> Fetch product detail with document + ECO summary\n"
DETAIL_RESP="$(
  $CURL "$API/products/$PART_ID?include_versions=false&include_files=false&include_document_summary=true&include_eco_summary=true" \
    "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

DETAIL_JSON="$DETAIL_RESP" PART_ID="$PART_ID" DOC_ID="$DOC_ID" ECO_ID="$ECO_ID" "$PY" - <<'PY'
import os
import json

data = json.loads(os.environ["DETAIL_JSON"])
doc_summary = data.get("document_summary") or {}
eco_summary = data.get("eco_summary") or {}

if doc_summary.get("authorized") is False:
    raise SystemExit("document summary unauthorized")
if doc_summary.get("count", 0) < 1:
    raise SystemExit("expected document summary count >= 1")

eco_count = eco_summary.get("count", 0)
if eco_summary.get("authorized") is False or eco_count < 1:
    raise SystemExit("expected eco summary count >= 1")

pending = eco_summary.get("pending_approvals") or {}
if pending.get("count", 0) < 1:
    raise SystemExit("expected pending approval count >= 1")

print("Docs + ECO UI summary: OK")
PY

printf "\n==============================================\n"
printf "Docs + ECO UI Summary Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
