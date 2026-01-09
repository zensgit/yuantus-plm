#!/usr/bin/env bash
# =============================================================================
# Docs + Approval Verification
# Runs document checks and a basic ECO approval flow.
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

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

fail() { echo "FAIL: $1"; exit 1; }
ok() { echo "OK: $1"; }

printf "==============================================\n"
printf "Docs + Approval Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Documents & Files\n"
bash scripts/verify_documents.sh "$BASE_URL" "$TENANT" "$ORG"
ok "Documents & files verified"

printf "\n==> Document lifecycle\n"
bash scripts/verify_document_lifecycle.sh "$BASE_URL" "$TENANT" "$ORG"
ok "Document lifecycle verified"

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
STAGE_NAME="DOC-APPROVAL-$TS"

printf "\n==> Create approval stage\n"
STAGE_RESP="$(
  $CURL -X POST "$API/eco/stages" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"$STAGE_NAME\",\"sequence\":80,\"approval_type\":\"mandatory\",\"approval_roles\":[\"admin\"],\"auto_progress\":false,\"is_blocking\":false,\"sla_hours\":0}"
)"
STAGE_ID="$(echo "$STAGE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$STAGE_ID" ]]; then
  echo "Response: $STAGE_RESP"
  fail "Failed to create approval stage"
fi
ok "Created stage: $STAGE_ID"

printf "\n==> Create ECO product\n"
PRODUCT_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"DOC-APPROVAL-P-$TS\",\"name\":\"Approval Product\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$PRODUCT_ID" ]]; then
  fail "Failed to create product"
fi
ok "Created product: $PRODUCT_ID"

printf "\n==> Create ECO\n"
ECO_RESP="$(
  $CURL -X POST "$API/eco" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"ECO-APPROVAL-$TS\",\"eco_type\":\"bom\",\"product_id\":\"$PRODUCT_ID\",\"description\":\"doc approval test\"}"
)"
ECO_ID="$(echo "$ECO_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$ECO_ID" ]]; then
  echo "Response: $ECO_RESP"
  fail "Failed to create ECO"
fi
ok "Created ECO: $ECO_ID"

printf "\n==> Move ECO to approval stage\n"
MOVE_RESP="$(
  $CURL -X POST "$API/eco/$ECO_ID/move-stage" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"stage_id\":\"$STAGE_ID\"}"
)"
MOVE_STAGE_ID="$(echo "$MOVE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("stage_id",""))')"
if [[ "$MOVE_STAGE_ID" != "$STAGE_ID" ]]; then
  echo "Response: $MOVE_RESP"
  fail "Failed to move ECO to approval stage"
fi
ok "Moved ECO to stage"

printf "\n==> Approve ECO\n"
APPROVE_RESP="$(
  $CURL -X POST "$API/eco/$ECO_ID/approve" "${HEADERS[@]}" "${ADMIN_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"comment\":\"approve\"}"
)"
APPROVAL_ID="$(echo "$APPROVE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$APPROVAL_ID" ]]; then
  echo "Response: $APPROVE_RESP"
  fail "Failed to approve ECO"
fi
ok "Approved ECO: $APPROVAL_ID"

printf "\n==> Verify ECO state and approvals\n"
ECO_STATE_RESP="$(
  $CURL "$API/eco/$ECO_ID" "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"
APPROVALS_RESP="$(
  $CURL "$API/eco/$ECO_ID/approvals" "${HEADERS[@]}" "${ADMIN_AUTH[@]}"
)"

ECO_JSON="$ECO_STATE_RESP" APPROVALS_JSON="$APPROVALS_RESP" "$PY" - <<'PY'
import os
import json

eco = json.loads(os.environ["ECO_JSON"])
approvals = json.loads(os.environ["APPROVALS_JSON"])

state = eco.get("state")
if state != "approved":
    raise SystemExit(f"Expected ECO state approved, got {state}")

if not approvals:
    raise SystemExit("Missing approvals list")

status = approvals[0].get("status")
if status != "approved":
    raise SystemExit(f"Expected approval status approved, got {status}")

print("Approval flow: OK")
PY

printf "\n==============================================\n"
printf "Docs + Approval Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
