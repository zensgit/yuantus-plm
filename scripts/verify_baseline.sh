#!/usr/bin/env bash
# =============================================================================
# Baseline Verification Script
# Verifies baseline snapshot creation + compare against current BOM.
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

TS="$(date +%s)"

echo "=============================================="
echo "Baseline Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
"$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
"$CLI" seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || "$CLI" seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login as admin"
ADMIN_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

echo ""
echo "==> Create parent + children"
PARENT_ID="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-A-$TS\",\"name\":\"Baseline Parent\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
CHILD_B="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-B-$TS\",\"name\":\"Child B\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
CHILD_C="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-C-$TS\",\"name\":\"Child C\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$PARENT_ID" || -z "$CHILD_B" || -z "$CHILD_C" ]]; then
  fail "Failed to create parent/children"
fi
ok "Created parent=$PARENT_ID children=$CHILD_B,$CHILD_C"

echo ""
echo "==> Build BOM (A -> B, C)"
$CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_B\",\"quantity\":1,\"uom\":\"EA\"}" >/dev/null
$CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_C\",\"quantity\":2,\"uom\":\"EA\"}" >/dev/null
ok "BOM created"

echo ""
echo "==> Create baseline"
BASELINE_RESP="$(
  $CURL -X POST "$API/baselines" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"name\":\"BL-$TS\",\"description\":\"Baseline test\",\"root_item_id\":\"$PARENT_ID\",\"max_levels\":10}"
)"
BASELINE_ID="$(echo "$BASELINE_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$BASELINE_ID" ]]; then
  echo "Response: $BASELINE_RESP"
  fail "Baseline create failed"
fi

RESP_JSON="$BASELINE_RESP" "$PY" - <<'PY'
import os, json
resp = json.loads(os.environ.get("RESP_JSON", "{}"))
assert resp.get("item_count", 0) >= 3
assert resp.get("relationship_count", 0) >= 2
snap = resp.get("snapshot") or {}
children = snap.get("children") or []
assert len(children) == 2
print("Baseline snapshot validated")
PY
ok "Baseline created: $BASELINE_ID"

echo ""
echo "==> Compare baseline vs current (expect no diffs)"
COMPARE_RESP="$($CURL -X POST "$API/baselines/$BASELINE_ID/compare" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"target_type\":\"item\",\"target_id\":\"$PARENT_ID\",\"max_levels\":10}")"
RESP_JSON="$COMPARE_RESP" "$PY" - <<'PY'
import os, json
resp = json.loads(os.environ.get("RESP_JSON", "{}"))
summary = resp.get("summary") or {}
assert summary.get("added", 0) == 0
assert summary.get("removed", 0) == 0
assert summary.get("changed", 0) == 0
print("No diff as expected")
PY
ok "Baseline compare (no diff)"

echo ""
echo "==> Modify BOM (change qty + add new child)"
CHILD_D="$(
  $CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-D-$TS\",\"name\":\"Child D\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$CHILD_D" ]]; then
  fail "Failed to create Child D"
fi

# Remove B then re-add with new quantity (should show as changed)
$CURL -X DELETE "$API/bom/$PARENT_ID/children/$CHILD_B" "${HEADERS[@]}" "${AUTH[@]}" >/dev/null
$CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_B\",\"quantity\":3,\"uom\":\"EA\"}" >/dev/null

# Add new child D (should show as added)
$CURL -X POST "$API/bom/$PARENT_ID/children" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"child_id\":\"$CHILD_D\",\"quantity\":1,\"uom\":\"EA\"}" >/dev/null
ok "BOM updated"

echo ""
echo "==> Compare baseline vs current (expect added + changed)"
COMPARE_RESP="$($CURL -X POST "$API/baselines/$BASELINE_ID/compare" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"target_type\":\"item\",\"target_id\":\"$PARENT_ID\",\"max_levels\":10}")"
RESP_JSON="$COMPARE_RESP" "$PY" - <<'PY'
import os, json
resp = json.loads(os.environ.get("RESP_JSON", "{}"))
summary = resp.get("summary") or {}
added = summary.get("added", 0)
changed = summary.get("changed", 0)
assert added >= 1, f"expected added>=1, got {added}"
assert changed >= 1, f"expected changed>=1, got {changed}"
print("Diff validated")
PY
ok "Baseline compare (diff)"

echo ""
echo "==> Create new baseline and compare baseline-to-baseline"
BASELINE2_RESP="$($CURL -X POST "$API/baselines" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"name\":\"BL2-$TS\",\"root_item_id\":\"$PARENT_ID\",\"max_levels\":10}")"
BASELINE2_ID="$(echo "$BASELINE2_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$BASELINE2_ID" ]]; then
  echo "Response: $BASELINE2_RESP"
  fail "Baseline2 create failed"
fi

COMPARE_RESP="$($CURL -X POST "$API/baselines/$BASELINE_ID/compare" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"target_type\":\"baseline\",\"target_id\":\"$BASELINE2_ID\",\"max_levels\":10}")"
RESP_JSON="$COMPARE_RESP" "$PY" - <<'PY'
import os, json
resp = json.loads(os.environ.get("RESP_JSON", "{}"))
summary = resp.get("summary") or {}
assert summary.get("added", 0) >= 1
assert summary.get("changed", 0) >= 1
print("Baseline-to-baseline diff validated")
PY
ok "Baseline2 compare"

echo ""
echo "=============================================="
echo "Baseline Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
