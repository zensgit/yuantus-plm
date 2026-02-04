#!/usr/bin/env bash
# =============================================================================
# Product UI Aggregation Verification
# Verifies BOM summary + where-used + obsolete + weight rollup summaries on product detail endpoint.
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
admin_uid = int(os.environ.get("ADMIN_UID") or random.randint(400000, 900000))
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

def create_part(item_number: str, name: str, extra: dict | None = None) -> str:
    resp = client.post(
        "/api/v1/aml/apply",
        headers=auth_headers,
        json={
            "type": "Part",
            "action": "add",
            "properties": {"item_number": item_number, "name": name, **(extra or {})},
        },
    )
    resp.raise_for_status()
    item_id = resp.json().get("id")
    if not item_id:
        raise SystemExit("Failed to create part")
    return item_id

parent_id = create_part(f"PROD-UI-P-{ts}", f"Product UI Parent {ts}")
child_id = create_part(
    f"PROD-UI-C-{ts}", f"Product UI Child {ts}", {"weight": "2.0"}
)
obs_child_id = create_part(
    f"PROD-UI-OBS-{ts}",
    f"Product UI Obsolete {ts}",
    {"weight": "1.5", "obsolete": True},
)

resp = client.post(
    f"/api/v1/bom/{parent_id}/children",
    headers=auth_headers,
    json={"child_id": child_id, "quantity": 1, "uom": "EA"},
)
resp.raise_for_status()
rel_id = resp.json().get("relationship_id")
if not rel_id:
    raise SystemExit("Failed to add BOM child")

resp = client.post(
    f"/api/v1/bom/{parent_id}/children",
    headers=auth_headers,
    json={"child_id": obs_child_id, "quantity": 2, "uom": "EA"},
)
resp.raise_for_status()

parent_detail = client.get(
    f"/api/v1/products/{parent_id}",
    headers=auth_headers,
    params={
        "include_versions": "false",
        "include_files": "false",
        "include_bom_summary": "true",
        "bom_summary_depth": "2",
        "include_where_used_summary": "true",
        "include_bom_obsolete_summary": "true",
        "include_bom_weight_rollup": "true",
        "bom_weight_levels": "1",
    },
)
parent_detail.raise_for_status()

child_detail = client.get(
    f"/api/v1/products/{child_id}",
    headers=auth_headers,
    params={
        "include_versions": "false",
        "include_files": "false",
        "include_bom_summary": "true",
        "include_where_used_summary": "true",
        "where_used_recursive": "true",
        "where_used_max_levels": "3",
    },
)
child_detail.raise_for_status()

parent = parent_detail.json()
child = child_detail.json()

bom_summary = parent.get("bom_summary") or {}
if not bom_summary or bom_summary.get("authorized") is False:
    raise SystemExit("missing or unauthorized bom_summary for parent")
if bom_summary.get("direct_children", 0) < 1:
    raise SystemExit("expected direct_children >= 1")

wu_parent = parent.get("where_used_summary") or {}
if wu_parent.get("authorized") is False:
    raise SystemExit("unexpected where_used unauthorized")

wu_child = child.get("where_used_summary") or {}
if wu_child.get("authorized") is False:
    raise SystemExit("missing where_used_summary for child")
if wu_child.get("count", 0) < 1:
    raise SystemExit("expected where_used count >= 1")

sample = wu_child.get("sample") or []
if not sample:
    raise SystemExit("missing where-used sample")
sample_parent = sample[0]
if sample_parent.get("id") != parent_id:
    raise SystemExit("where-used sample parent mismatch")

obs_summary = parent.get("bom_obsolete_summary") or {}
if obs_summary.get("authorized") is False:
    raise SystemExit("missing bom_obsolete_summary")
if obs_summary.get("count", 0) < 1:
    raise SystemExit("expected obsolete count >= 1")
obs_sample = obs_summary.get("sample") or []
if not obs_sample:
    raise SystemExit("missing obsolete sample")
if not any(entry.get("child_id") == obs_child_id for entry in obs_sample):
    raise SystemExit("obsolete sample missing child id")

rollup = parent.get("bom_weight_rollup_summary") or {}
if rollup.get("authorized") is False:
    raise SystemExit("missing bom_weight_rollup_summary")
total_weight = rollup.get("total_weight")
if total_weight is None or abs(float(total_weight) - 5.0) > 1e-6:
    raise SystemExit(f"unexpected total_weight: {total_weight}")

print("ALL CHECKS PASSED")
PY
  exit 0
fi

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

printf "==============================================\n"
printf "Product UI Aggregation Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
RAND_BASE=$(( (RANDOM << 16) | RANDOM ))
ADMIN_UID="${ADMIN_UID:-$((RAND_BASE + 400000))}"
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
PARENT_NUM="PROD-UI-P-$TS"
CHILD_NUM="PROD-UI-C-$TS"

create_part() {
  local num="$1"
  local name="$2"
  local extra_props="${3:-}"
  local props="\"item_number\":\"$num\",\"name\":\"$name\""
  if [[ -n "$extra_props" ]]; then
    props="$props,$extra_props"
  fi
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{$props}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
}

printf "\n==> Create Parts\n"
PARENT_ID="$(create_part "$PARENT_NUM" "Product UI Parent $TS")"
CHILD_ID="$(create_part "$CHILD_NUM" "Product UI Child $TS" "\"weight\":\"2.0\"")"
OBS_CHILD_ID="$(create_part "PROD-UI-OBS-$TS" "Product UI Obsolete $TS" "\"weight\":\"1.5\",\"obsolete\":true")"
if [[ -z "$PARENT_ID" || -z "$CHILD_ID" || -z "$OBS_CHILD_ID" ]]; then
  fail "Failed to create parts"
fi
ok "Created Parts: parent=$PARENT_ID child=$CHILD_ID obsolete_child=$OBS_CHILD_ID"

printf "\n==> Add BOM child\n"
REL_RESP="$(
  $CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$CHILD_ID\",\"quantity\":1,\"uom\":\"EA\"}"
)"
REL_ID="$(echo "$REL_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_ID" ]]; then
  echo "Response: $REL_RESP"
  fail "Failed to add BOM child"
fi
ok "Added BOM line: $REL_ID"

printf "\n==> Add BOM obsolete child\n"
REL_OBS_RESP="$(
  $CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$OBS_CHILD_ID\",\"quantity\":2,\"uom\":\"EA\"}"
)"
REL_OBS_ID="$(echo "$REL_OBS_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("relationship_id",""))')"
if [[ -z "$REL_OBS_ID" ]]; then
  echo "Response: $REL_OBS_RESP"
  fail "Failed to add obsolete BOM child"
fi
ok "Added obsolete BOM line: $REL_OBS_ID"

printf "\n==> Fetch parent product detail with BOM summary\n"
PARENT_DETAIL="$(
  $CURL "$API/products/$PARENT_ID?include_versions=false&include_files=false&include_bom_summary=true&bom_summary_depth=2&include_where_used_summary=true&include_bom_obsolete_summary=true&include_bom_weight_rollup=true&bom_weight_levels=1" \
    "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

printf "\n==> Fetch child product detail with where-used summary\n"
CHILD_DETAIL="$(
  $CURL "$API/products/$CHILD_ID?include_versions=false&include_files=false&include_bom_summary=true&include_where_used_summary=true&where_used_recursive=true&where_used_max_levels=3" \
    "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

PARENT_JSON="$PARENT_DETAIL" CHILD_JSON="$CHILD_DETAIL" PARENT_ID="$PARENT_ID" OBS_CHILD_ID="$OBS_CHILD_ID" "$PY" - <<'PY'
import os
import json
import math

parent = json.loads(os.environ["PARENT_JSON"])
child = json.loads(os.environ["CHILD_JSON"])
parent_id = os.environ["PARENT_ID"]
obs_child_id = os.environ["OBS_CHILD_ID"]

bom_summary = parent.get("bom_summary") or {}
if not bom_summary or bom_summary.get("authorized") is False:
    raise SystemExit("missing or unauthorized bom_summary for parent")
if bom_summary.get("direct_children", 0) < 1:
    raise SystemExit("expected direct_children >= 1")

wu_parent = parent.get("where_used_summary") or {}
if wu_parent.get("authorized") is False:
    raise SystemExit("unexpected where_used unauthorized")

wu_child = child.get("where_used_summary") or {}
if wu_child.get("authorized") is False:
    raise SystemExit("missing where_used_summary for child")
if wu_child.get("count", 0) < 1:
    raise SystemExit("expected where_used count >= 1")

sample = wu_child.get("sample") or []
if not sample:
    raise SystemExit("missing where-used sample")
sample_parent = sample[0]
if sample_parent.get("id") != parent_id:
    raise SystemExit("where-used sample parent mismatch")

obs_summary = parent.get("bom_obsolete_summary") or {}
if obs_summary.get("authorized") is False:
    raise SystemExit("missing bom_obsolete_summary")
if obs_summary.get("count", 0) < 1:
    raise SystemExit("expected obsolete count >= 1")
obs_sample = obs_summary.get("sample") or []
if not obs_sample:
    raise SystemExit("missing obsolete sample")
if not any(entry.get("child_id") == obs_child_id for entry in obs_sample):
    raise SystemExit("obsolete sample missing child id")

rollup = parent.get("bom_weight_rollup_summary") or {}
if rollup.get("authorized") is False:
    raise SystemExit("missing bom_weight_rollup_summary")
total_weight = rollup.get("total_weight")
if total_weight is None or not math.isclose(float(total_weight), 5.0, rel_tol=1e-6):
    raise SystemExit(f"unexpected total_weight: {total_weight}")

print("Product UI aggregation: OK")
PY

printf "\n==============================================\n"
printf "Product UI Aggregation Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
