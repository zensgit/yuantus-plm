#!/usr/bin/env bash
# =============================================================================
# ECO Advanced Verification Script
# Verifies:
# 1) Impact analysis (where-used + file attachments)
# 2) BOM diff between ECO source/target versions
# 3) Batch approvals (admin success, viewer denied)
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
DB_URL="${DB_URL:-}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"

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

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$DB_URL" || -n "$identity_url" ]]; then
    env \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

echo "=============================================="
echo "ECO Advanced Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

TS="$(date +%s)"

VIEWER_USER="viewer-$TS"
VIEWER_ID=$((10000 + (TS % 100000)))

echo ""
echo "==> Seed identity/meta"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username "$VIEWER_USER" --password viewer --user-id "$VIEWER_ID" --roles viewer --no-superuser >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login (admin + viewer)"
ADMIN_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
VIEWER_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"$VIEWER_USER\",\"password\":\"viewer\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$VIEWER_TOKEN" ]]; then
  fail "Viewer login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
VIEWER_HEADERS=(-H "Authorization: Bearer $VIEWER_TOKEN")
ok "Login succeeded"

echo ""
echo "==> Create ECO stage (approval_roles=admin)"
STAGE_NAME="S4-Review-$TS"
STAGE_ID="$(
  $CURL -X POST "$API/eco/stages" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"$STAGE_NAME\",\"sequence\":90,\"approval_type\":\"mandatory\",\"approval_roles\":[\"admin\"],\"auto_progress\":false,\"is_blocking\":false,\"sla_hours\":0}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$STAGE_ID" ]]; then
  fail "Failed to create ECO stage"
fi
ok "Stage created: $STAGE_ID"

echo ""
echo "==> Create product + assembly"
PRODUCT_ID="$(
  $CURL -X POST "$API/aml/apply" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"ECO-P-$TS\",\"name\":\"ECO Product $TS\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
ASSEMBLY_ID="$(
  $CURL -X POST "$API/aml/apply" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"ECO-A-$TS\",\"name\":\"ECO Assembly $TS\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$PRODUCT_ID" || -z "$ASSEMBLY_ID" ]]; then
  fail "Failed to create product/assembly"
fi
ok "Created product: $PRODUCT_ID"
ok "Created assembly: $ASSEMBLY_ID"

echo ""
echo "==> Init product version"
INIT_RESP="$(
  $CURL -X POST "$API/versions/items/$PRODUCT_ID/init" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
INIT_VERSION_ID="$(echo "$INIT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$INIT_VERSION_ID" ]]; then
  echo "Response: $INIT_RESP"
  fail "Failed to init product version"
fi
ok "Initial version: $INIT_VERSION_ID"

echo ""
echo "==> Build where-used link (assembly -> product)"
WU_RESP="$(
  $CURL -X POST "$API/bom/$ASSEMBLY_ID/children" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"child_id\":\"$PRODUCT_ID\",\"quantity\":1,\"uom\":\"EA\"}"
)"
WU_OK="$(echo "$WU_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("ok",False))')"
if [[ "$WU_OK" != "True" ]]; then
  echo "Response: $WU_RESP"
  fail "Failed to create where-used link"
fi
ok "Where-used link created"

echo ""
echo "==> Upload file + attach to product"
TMP_FILE="/tmp/yuantus_eco_impact_$TS.txt"
echo "yuantus eco impact verification $TS" > "$TMP_FILE"
FILE_ID="$(
  $CURL -X POST "$API/file/upload?generate_preview=false" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$TMP_FILE" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$FILE_ID" ]]; then
  fail "Failed to upload file"
fi
ATTACH_RESP="$(
  $CURL -X POST "$API/file/attach" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"item_id\":\"$PRODUCT_ID\",\"file_id\":\"$FILE_ID\",\"file_role\":\"spec\"}"
)"
ATTACH_STATUS="$(echo "$ATTACH_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status",""))')"
if [[ -z "$ATTACH_STATUS" ]]; then
  echo "Response: $ATTACH_RESP"
  fail "Failed to attach file"
fi
ok "File attached (status=$ATTACH_STATUS)"

echo ""
echo "==> Create ECO (for product)"
ECO1_ID="$(
  $CURL -X POST "$API/eco" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"ECO-ADV-$TS\",\"eco_type\":\"bom\",\"product_id\":\"$PRODUCT_ID\",\"description\":\"ECO advanced verification\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$ECO1_ID" ]]; then
  fail "Failed to create ECO1"
fi
ok "ECO1 created: $ECO1_ID"

echo ""
echo "==> Move ECO1 to approval stage"
$CURL -X POST "$API/eco/$ECO1_ID/move-stage" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -H 'content-type: application/json' \
  -d "{\"stage_id\":\"$STAGE_ID\"}" >/dev/null
ok "ECO1 moved to stage"

echo ""
echo "==> SLA overdue check + notify"
OVERDUE_RESP="$(
  $CURL "$API/eco/approvals/overdue" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
RESP_JSON="$OVERDUE_RESP" ECO1_ID="$ECO1_ID" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
data = json.loads(raw or "[]")
eco_id = os.environ.get("ECO1_ID")
ids = [d.get("eco_id") for d in data if isinstance(d, dict)]
if eco_id not in ids:
    raise SystemExit("Expected ECO1 in overdue list")
print("Overdue list: OK")
PY
ok "Overdue list validated"

NOTIFY_RESP="$(
  $CURL -X POST "$API/eco/approvals/notify-overdue" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
RESP_JSON="$NOTIFY_RESP" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
data = json.loads(raw or "{}")
if data.get("count", 0) < 1 or data.get("notified", 0) < 1:
    raise SystemExit("Expected overdue notifications")
print("Overdue notifications: OK")
PY
ok "Overdue notifications sent"

echo ""
echo "==> Create ECO target version"
NEW_REV_RESP="$(
  $CURL -X POST "$API/eco/$ECO1_ID/new-revision" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
TARGET_VERSION_ID="$(echo "$NEW_REV_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("version_id",""))')"
if [[ -z "$TARGET_VERSION_ID" ]]; then
  echo "Response: $NEW_REV_RESP"
  fail "Failed to create new revision"
fi
ok "Target version: $TARGET_VERSION_ID"

echo ""
echo "==> Resolve target version timestamp"
TREE_RESP="$(
  $CURL "$API/versions/items/$PRODUCT_ID/tree" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
TARGET_CREATED_AT="$(
  TREE_JSON="$TREE_RESP" TARGET_VERSION_ID="$TARGET_VERSION_ID" "$PY" - <<'PY'
import os, json
data = json.loads(os.environ.get("TREE_JSON", "[]"))
target_id = os.environ.get("TARGET_VERSION_ID")
created = ""
for node in data:
    if node.get("id") == target_id:
        created = node.get("created_at") or ""
        break
print(created)
PY
)"
if [[ -z "$TARGET_CREATED_AT" ]]; then
  echo "Tree: $TREE_RESP"
  fail "Failed to resolve target version created_at"
fi
ok "Target created_at: $TARGET_CREATED_AT"

echo ""
echo "==> Add new BOM line effective from target version date"
CHILD_ID="$(
  $CURL -X POST "$API/aml/apply" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"ECO-C-$TS\",\"name\":\"ECO Child $TS\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$CHILD_ID" ]]; then
  fail "Failed to create child part"
fi

ADD_PAYLOAD="$(printf '{"child_id":"%s","quantity":1,"uom":"EA","effectivity_from":"%s"}' "$CHILD_ID" "$TARGET_CREATED_AT")"
ADD_RESP="$(
  $CURL -X POST "$API/bom/$PRODUCT_ID/children" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "$ADD_PAYLOAD"
)"
ADD_OK="$(echo "$ADD_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("ok",False))')"
if [[ "$ADD_OK" != "True" ]]; then
  echo "Response: $ADD_RESP"
  fail "Failed to add effective BOM line"
fi
ok "Effective BOM line added"

echo ""
echo "==> ECO BOM diff (expect added child)"
DIFF_RESP="$(
  $CURL "$API/eco/$ECO1_ID/bom-diff?max_levels=5&include_relationship_props=quantity" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
RESP_JSON="$DIFF_RESP" CHILD_ID="$CHILD_ID" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /eco/{eco_id}/bom-diff")
data = json.loads(raw)
summary = data.get("summary", {})
added = data.get("added", [])
child_id = os.environ.get("CHILD_ID")

def ids(entries):
    out = set()
    for e in entries:
        cid = e.get("child_id")
        if not cid:
            child = e.get("child") or {}
            cid = child.get("id")
        if cid:
            out.add(cid)
    return out

added_ids = ids(added)
if summary.get("added", len(added)) < 1:
    raise SystemExit("Expected >=1 added BOM lines")
if child_id not in added_ids:
    raise SystemExit("Expected child id in added set")
print("BOM diff: OK")
PY
ok "BOM diff validated"

echo ""
echo "==> ECO BOM diff (compare_mode=only_product)"
DIFF_ONLY_RESP="$(
  $CURL "$API/eco/$ECO1_ID/bom-diff?max_levels=5&compare_mode=only_product" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
RESP_JSON="$DIFF_ONLY_RESP" CHILD_ID="$CHILD_ID" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /eco/{eco_id}/bom-diff (only_product)")
data = json.loads(raw)
summary = data.get("summary", {})
changed = data.get("changed", [])
added = data.get("added", [])
child_id = os.environ.get("CHILD_ID")

if summary.get("changed", 0) != 0 or changed:
    raise SystemExit("only_product should not report changed entries")

added_ids = {e.get("child_id") or (e.get("child") or {}).get("id") for e in added}
if child_id not in added_ids:
    raise SystemExit("Expected child id in added set (only_product)")

print("BOM diff only_product: OK")
PY
ok "BOM diff compare_mode validated"

echo ""
echo "==> ECO impact analysis (include files + bom diff + version diff)"
IMPACT_RESP="$(
  $CURL "$API/eco/$ECO1_ID/impact?include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity&include_child_fields=true" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
RESP_JSON="$IMPACT_RESP" ASSEMBLY_ID="$ASSEMBLY_ID" FILE_ID="$FILE_ID" CHILD_ID="$CHILD_ID" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
if not raw:
    raise SystemExit("Empty response from /eco/{eco_id}/impact")
data = json.loads(raw)
impact_count = data.get("impact_count", 0)
if impact_count < 1:
    raise SystemExit("Expected impact_count >= 1")

assemblies = data.get("impacted_assemblies") or []
parent_ids = [a.get("parent", {}).get("id") for a in assemblies if isinstance(a, dict)]
assembly_id = os.environ.get("ASSEMBLY_ID")
if assembly_id not in parent_ids:
    raise SystemExit("Expected assembly to appear in impacted_assemblies")

files = data.get("files") or {}
item_files = files.get("item_files") or []
file_id = os.environ.get("FILE_ID")
if not any(f.get("file_id") == file_id for f in item_files):
    raise SystemExit("Expected attached file in files.item_files")

child_id = os.environ.get("CHILD_ID")
bom_diff = data.get("bom_diff") or {}
summary = bom_diff.get("summary") or {}
added = bom_diff.get("added") or []
added_ids = {e.get("child_id") or (e.get("child") or {}).get("id") for e in added}
if summary.get("added", 0) < 1:
    raise SystemExit("Expected bom_diff.summary.added >= 1")
if child_id not in added_ids:
    raise SystemExit("Expected child id in bom_diff.added")

version_diff = data.get("version_diff")
if version_diff is None:
    raise SystemExit("Expected version_diff in impact response")
if not isinstance(version_diff.get("diffs", {}), dict):
    raise SystemExit("Expected version_diff.diffs to be a dict")

version_files_diff = data.get("version_files_diff")
if version_files_diff is None:
    raise SystemExit("Expected version_files_diff in impact response")
summary_files = version_files_diff.get("summary") or {}
for key in ("added_count", "removed_count", "modified_count"):
    if key not in summary_files:
        raise SystemExit(f"Missing version_files_diff.summary.{key}")

impact_level = data.get("impact_level")
if impact_level not in {"high", "medium", "low", "none"}:
    raise SystemExit("Missing or invalid impact_level")
impact_scope = data.get("impact_scope")
if not impact_scope:
    raise SystemExit("Missing impact_scope")
impact_summary = data.get("impact_summary") or {}
if impact_summary.get("added", 0) < 1:
    raise SystemExit("Expected impact_summary.added >= 1")
if impact_summary.get("added") != summary.get("added"):
    raise SystemExit("impact_summary and bom_diff.summary mismatch")
if impact_level != "high":
    raise SystemExit(f"Expected impact_level=high, got {impact_level}")
print("Impact analysis: OK")
PY
ok "Impact analysis validated"

echo ""
echo "==> ECO impact export (csv/xlsx/pdf)"
CSV_OUT="/tmp/yuantus_eco_impact_${TS}.csv"
CSV_CODE="$(
  $CURL -o "$CSV_OUT" -w '%{http_code}' \
    "$API/eco/$ECO1_ID/impact/export?format=csv&include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity&compare_mode=only_product" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
if [[ "$CSV_CODE" != "200" ]]; then
  fail "CSV export failed (HTTP $CSV_CODE)"
fi
if ! grep -q "# Overview" "$CSV_OUT"; then
  fail "CSV export missing Overview section"
fi

XLSX_OUT="/tmp/yuantus_eco_impact_${TS}.xlsx"
XLSX_CODE="$(
  $CURL -o "$XLSX_OUT" -w '%{http_code}' \
    "$API/eco/$ECO1_ID/impact/export?format=xlsx&include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
if [[ "$XLSX_CODE" != "200" ]]; then
  fail "XLSX export failed (HTTP $XLSX_CODE)"
fi

PDF_OUT="/tmp/yuantus_eco_impact_${TS}.pdf"
PDF_CODE="$(
  $CURL -o "$PDF_OUT" -w '%{http_code}' \
    "$API/eco/$ECO1_ID/impact/export?format=pdf&include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}"
)"
if [[ "$PDF_CODE" != "200" ]]; then
  fail "PDF export failed (HTTP $PDF_CODE)"
fi

"$PY" - <<PY
import pathlib

csv_path = pathlib.Path("$CSV_OUT")
xlsx_path = pathlib.Path("$XLSX_OUT")
pdf_path = pathlib.Path("$PDF_OUT")
csv_text = csv_path.read_text(encoding="utf-8", errors="ignore")

if csv_path.stat().st_size == 0:
    raise SystemExit("CSV export is empty")
if xlsx_path.read_bytes()[:2] != b"PK":
    raise SystemExit("XLSX export missing PK header")
if not pdf_path.read_bytes().startswith(b"%PDF"):
    raise SystemExit("PDF export missing %PDF header")
if "bom_compare_mode,only_product" not in csv_text:
    raise SystemExit("CSV export missing bom_compare_mode")
if "bom_line_key,child_config" not in csv_text:
    raise SystemExit("CSV export missing bom_line_key")
print("Impact export files: OK")
PY
ok "Impact export validated"

echo ""
echo "==> Create ECO2 for batch approvals"
PRODUCT2_ID="$(
  $CURL -X POST "$API/aml/apply" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"ECO-P2-$TS\",\"name\":\"ECO Product 2 $TS\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$PRODUCT2_ID" ]]; then
  fail "Failed to create product2"
fi
ECO2_ID="$(
  $CURL -X POST "$API/eco" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"ECO-ADV2-$TS\",\"eco_type\":\"bom\",\"product_id\":\"$PRODUCT2_ID\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$ECO2_ID" ]]; then
  fail "Failed to create ECO2"
fi
$CURL -X POST "$API/eco/$ECO2_ID/move-stage" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -H 'content-type: application/json' \
  -d "{\"stage_id\":\"$STAGE_ID\"}" >/dev/null
ok "ECO2 created/moved: $ECO2_ID"

echo ""
echo "==> Batch approve as admin"
BATCH_APPROVE_RESP="$(
  $CURL -X POST "$API/eco/approvals/batch" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"eco_ids\":[\"$ECO1_ID\",\"$ECO2_ID\"],\"mode\":\"approve\",\"comment\":\"batch approve\"}"
)"
RESP_JSON="$BATCH_APPROVE_RESP" ECO1_ID="$ECO1_ID" ECO2_ID="$ECO2_ID" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
data = json.loads(raw)
results = data.get("results") or []
summary = data.get("summary") or {}
status = {r.get("eco_id"): r.get("ok") for r in results}
eco1 = os.environ.get("ECO1_ID")
eco2 = os.environ.get("ECO2_ID")
if status.get(eco1) is not True or status.get(eco2) is not True:
    raise SystemExit("Expected both approvals to succeed")
if summary.get("ok", 0) < 2:
    raise SystemExit("Expected summary.ok >= 2")
print("Batch approvals (admin): OK")
PY
ok "Admin batch approvals validated"

echo ""
echo "==> Verify ECO states are approved"
STATE1="$(
  $CURL "$API/eco/$ECO1_ID" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))'
)"
STATE2="$(
  $CURL "$API/eco/$ECO2_ID" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))'
)"
if [[ "$STATE1" != "approved" || "$STATE2" != "approved" ]]; then
  fail "ECO state not approved (eco1=$STATE1, eco2=$STATE2)"
fi
ok "ECO states approved"

echo ""
echo "==> Batch approve as viewer (expect denied)"
BATCH_VIEWER_RESP="$(
  $CURL -X POST "$API/eco/approvals/batch" \
    "${HEADERS[@]}" "${VIEWER_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d "{\"eco_ids\":[\"$ECO1_ID\",\"$ECO2_ID\"],\"mode\":\"approve\"}"
)"
RESP_JSON="$BATCH_VIEWER_RESP" ECO1_ID="$ECO1_ID" ECO2_ID="$ECO2_ID" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
data = json.loads(raw)
results = data.get("results") or []
status = {r.get("eco_id"): r.get("ok") for r in results}
eco1 = os.environ.get("ECO1_ID")
eco2 = os.environ.get("ECO2_ID")
if status.get(eco1) is not False or status.get(eco2) is not False:
    raise SystemExit("Expected viewer approvals to fail")
print("Batch approvals (viewer denied): OK")
PY
ok "Viewer batch approvals denied"

echo ""
echo "=============================================="
echo "ECO Advanced Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
