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
