#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
ATHENA_AUTH_TOKEN="${ATHENA_AUTH_TOKEN:-${ATHENA_TOKEN:-}}"
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

echo "==> Seed identity/meta"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null

echo "==> Login"
TOKEN="$(
  curl -s -X POST "$BASE/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'
)"

echo "==> Health"
curl -s "$BASE/api/v1/health" -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d["ok"] is True;print("Health: OK")'

echo "==> Meta metadata (Part)"
curl -s "$BASE/api/v1/aml/metadata/Part" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d["id"]=="Part";props=[p["name"] for p in d.get("properties",[])];assert "item_number" in props;print("Meta metadata: OK")'

TS="$(date +%s)"
PN="P-VERIFY-$TS"

echo "==> AML add/get"
PART_ID="$(
  curl -s "$BASE/api/v1/aml/apply" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$PN\",\"name\":\"Verify Part $TS\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "AML add: OK (part_id=$PART_ID)"

curl -s "$BASE/api/v1/aml/apply" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d "{\"type\":\"Part\",\"action\":\"get\",\"properties\":{\"item_number\":\"$PN\"}}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("count",0)>=1;print("AML get: OK")'

echo "==> Search"
curl -s "$BASE/api/v1/search/?q=$PN&item_type=Part" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("total",0)>=1;print("Search: OK")'

echo "==> RPC Item.create"
PN2="P-RPC-$TS"
RPC_ID="$(
  curl -s "$BASE/api/v1/rpc/" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"model\":\"Item\",\"method\":\"create\",\"args\":[{\"type\":\"Part\",\"properties\":{\"item_number\":\"$PN2\",\"name\":\"RPC Part\"}}],\"kwargs\":{}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["result"]["id"])'
)"
echo "RPC Item.create: OK (part_id=$RPC_ID)"

echo "==> File upload/download"
TEST_FILE=/tmp/yuantus_verify_test.txt
echo "yuantus verification test $(date)" > "$TEST_FILE"
FILE_ID="$(
  curl -s "$BASE/api/v1/file/upload?generate_preview=false" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -F "file=@$TEST_FILE" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "File upload: OK (file_id=$FILE_ID)"

curl -s "$BASE/api/v1/file/$FILE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d["id"];print("File metadata: OK")'

DOWNLOAD_URL="$BASE/api/v1/file/$FILE_ID/download"
HDRS=/tmp/yuantus_download_headers.txt

HTTP_CODE="$(
  curl -s -D "$HDRS" -o /tmp/yuantus_downloaded.txt -w '%{http_code}' \
    "$DOWNLOAD_URL" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG"
)"

if [[ "$HTTP_CODE" == "200" ]]; then
  : # local storage / streamed response
elif [[ "$HTTP_CODE" == "302" || "$HTTP_CODE" == "307" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "308" ]]; then
  LOCATION="$("$PY" - <<'PY'
import sys
path = "/tmp/yuantus_download_headers.txt"
loc = None
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if line.lower().startswith("location:"):
            loc = line.split(":", 1)[1].strip()
            break
if not loc:
    raise SystemExit("Missing Location header in redirect response")
print(loc)
PY
)"
  # Follow redirect without leaking API Authorization headers to S3.
  HTTP_CODE_2="$(curl -s -o /tmp/yuantus_downloaded.txt -w '%{http_code}' "$LOCATION")"
  [[ "$HTTP_CODE_2" == "200" ]] || (echo "Redirect download failed: HTTP $HTTP_CODE_2" >&2 && exit 1)
  HTTP_CODE="302->$HTTP_CODE_2"
else
  echo "Download failed: HTTP $HTTP_CODE" >&2
  exit 1
fi
diff -q "$TEST_FILE" /tmp/yuantus_downloaded.txt >/dev/null
echo "File download: OK (http=$HTTP_CODE)"

echo "==> BOM effective"
curl -s "$BASE/api/v1/bom/$PART_ID/effective" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert "children" in d;print("BOM effective: OK")'

echo "==> Plugins"
curl -s "$BASE/api/v1/plugins" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok") is True;print("Plugins list: OK")'
curl -s "$BASE/api/v1/plugins/demo/ping" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("ok") is True;print("Plugins ping: OK")'

echo "==> ECO full flow"
STAGE_NAME="Review-$TS"
STAGE_ID="$(
  curl -s -X POST "$BASE/api/v1/eco/stages" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"name\":\"$STAGE_NAME\",\"sequence\":10,\"approval_type\":\"mandatory\",\"approval_roles\":[\"admin\"]}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "ECO stage: OK (stage_id=$STAGE_ID)"

ECO_NAME="ECO-VERIFY-$TS"
ECO_ID="$(
  curl -s -X POST "$BASE/api/v1/eco" \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    -d "{\"name\":\"$ECO_NAME\",\"eco_type\":\"bom\",\"product_id\":\"$PART_ID\",\"description\":\"Verification ECO\",\"priority\":\"normal\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin)["id"])'
)"
echo "ECO create: OK (eco_id=$ECO_ID)"

NEWREV="$(curl -s -X POST "$BASE/api/v1/eco/$ECO_ID/new-revision" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")"
VERSION_ID="$(echo "$NEWREV" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("success") is True;print(d["version_id"])')"
echo "ECO new-revision: OK (version_id=$VERSION_ID)"

curl -s -X POST "$BASE/api/v1/eco/$ECO_ID/approve" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  -d '{"comment":"verification approved"}' \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("status")=="approved";print("ECO approve: OK")'

curl -s -X POST "$BASE/api/v1/eco/$ECO_ID/apply" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("success") is True;print("ECO apply: OK")'

echo "==> Versions history/tree"
curl -s "$BASE/api/v1/versions/items/$PART_ID/history" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert isinstance(d,list) and len(d)>=1;print("Versions history: OK")'
curl -s "$BASE/api/v1/versions/items/$PART_ID/tree" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert isinstance(d,list) and len(d)>=1;print("Versions tree: OK")'

echo "==> Integrations health (should be 200 even if services down)"
AUTH_HEADERS=(-H "Authorization: Bearer $TOKEN")
if [[ -n "$ATHENA_AUTH_TOKEN" ]]; then
  AUTH_HEADERS+=(-H "X-Athena-Authorization: Bearer $ATHENA_AUTH_TOKEN")
fi
HTTP_CODE="$(
  curl -s -o /tmp/yuantus_integrations.json -w '%{http_code}' \
    "$BASE/api/v1/integrations/health" \
    -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" \
    "${AUTH_HEADERS[@]}"
)"
[[ "$HTTP_CODE" == "200" ]] || (echo "Integrations health failed: HTTP $HTTP_CODE" >&2 && exit 1)
"$PY" -c 'import json;d=json.load(open("/tmp/yuantus_integrations.json"));assert "services" in d;print("Integrations health: OK (ok=%s)"%d.get("ok"))'

echo
echo "ALL CHECKS PASSED"
