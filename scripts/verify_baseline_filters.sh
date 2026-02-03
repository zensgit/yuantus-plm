#!/usr/bin/env bash
# =============================================================================
# Baseline List Filter Verification Script
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
if [[ "${CURL:-}" == *" "* ]]; then
  CURL_BIN="curl"
else
  CURL_BIN="${CURL:-curl}"
fi

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
  "$CLI" "$@"
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

ISO_FROM="2025-01-01T00:00:00Z"
ISO_TO="2025-12-31T23:59:59Z"

JSON_GET() {
  local url="$1"
  "$CURL_BIN" -sS "$url" "${HEADERS[@]}" -H "Authorization: Bearer $TOKEN"
}

require_key() {
  local json="$1"; shift
  local key="$1"
  printf '%s' "$json" | KEY="$key" "$PY" -c 'import json, sys, os
raw = sys.stdin.read()
if not raw:
    print("empty_response", file=sys.stderr)
    raise SystemExit(1)
try:
    obj = json.loads(raw)
except Exception as exc:
    print("invalid_json", exc, file=sys.stderr)
    print(raw[:500], file=sys.stderr)
    raise SystemExit(1)
key = os.environ.get("KEY", "")
if key not in obj:
    print(f"missing_key:{key}", file=sys.stderr)
    print(raw[:500], file=sys.stderr)
    raise SystemExit(1)
print("ok")'
}

assert_all_equal() {
  local json="$1"; shift
  local field="$1"; shift
  local expected="$1"
  printf '%s' "$json" | FIELD="$field" EXPECTED="$expected" "$PY" -c 'import json, sys, os
raw = sys.stdin.read()
obj = json.loads(raw)
field = os.environ.get("FIELD", "")
expected = os.environ.get("EXPECTED", "")
items = obj.get("items") or []
for item in items:
    if item.get(field) != expected:
        raise SystemExit("mismatch")
print("ok")'
}

assert_all_in_range() {
  local json="$1"; shift
  local field="$1"; shift
  local start="$1"; shift
  local end="$1"
  printf '%s' "$json" | FIELD="$field" START="$start" END="$end" "$PY" -c 'import json, sys, os
from datetime import datetime
raw = sys.stdin.read()
obj = json.loads(raw)
field = os.environ.get("FIELD", "")
start_raw = os.environ.get("START", "")
end_raw = os.environ.get("END", "")
items = obj.get("items") or []
if not items:
    print("ok")
    raise SystemExit(0)

def parse(dt):
    if not dt:
        return None
    if dt.endswith("Z"):
        dt = dt[:-1]
    return datetime.fromisoformat(dt)

start = parse(start_raw)
end = parse(end_raw)
for item in items:
    value = parse(item.get(field) or "")
    if value is None:
        raise SystemExit("missing")
    if start and value < start:
        raise SystemExit("out_of_range")
    if end and value > end:
        raise SystemExit("out_of_range")
print("ok")'
}

echo "=============================================="
echo "Baseline Filters Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

if ! "$CURL_BIN" -sS "$API/health" >/dev/null; then
  fail "API not reachable"
fi

run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Seeded identity + meta"

TOKEN="$("$CURL_BIN" -sS -X POST "$API/auth/login" -H 'content-type: application/json' -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$TOKEN" ]]; then
  fail "Admin login failed"
fi
ok "Admin login"

# Create a Part
PART_ID="$("$CURL_BIN" -sS -X POST "$API/aml/apply" -H 'content-type: application/json' -H "Authorization: Bearer $TOKEN" "${HEADERS[@]}" \
  -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"P-BL-FILTER\",\"name\":\"Baseline Filter Test\"}}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$PART_ID" ]]; then
  fail "Part create failed"
fi
ok "Created Part"

# Create baseline with explicit type/scope/state/effective_date
BASELINE_JSON="$("$CURL_BIN" -sS -X POST "$API/baselines" -H 'content-type: application/json' -H "Authorization: Bearer $TOKEN" "${HEADERS[@]}" \
  -d "{\"name\":\"BL Filter Test\",\"root_item_id\":\"$PART_ID\",\"baseline_type\":\"design\",\"scope\":\"product\",\"state\":\"released\",\"effective_date\":\"2025-06-01T00:00:00Z\",\"include_documents\":false,\"include_relationships\":false}" )"
BASELINE_ID="$(echo "$BASELINE_JSON" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$BASELINE_ID" ]]; then
  fail "Baseline create failed"
fi
ok "Created baseline"

# Filter by type/scope/state
RESP="$("$CURL_BIN" -sS "$API/baselines?baseline_type=design&scope=product&state=released&limit=50&offset=0" -H "Authorization: Bearer $TOKEN" "${HEADERS[@]}")"
require_key "$RESP" "items" >/dev/null || fail "Missing items"
assert_all_equal "$RESP" "baseline_type" "design" >/dev/null || fail "baseline_type filter failed"
assert_all_equal "$RESP" "scope" "product" >/dev/null || fail "scope filter failed"
assert_all_equal "$RESP" "state" "released" >/dev/null || fail "state filter failed"
ok "Type/scope/state filters"

# Filter by effective date range
RESP2="$("$CURL_BIN" -sS "$API/baselines?effective_from=$ISO_FROM&effective_to=$ISO_TO&limit=50&offset=0" -H "Authorization: Bearer $TOKEN" "${HEADERS[@]}")"
require_key "$RESP2" "items" >/dev/null || fail "Missing items"
assert_all_in_range "$RESP2" "effective_date" "$ISO_FROM" "$ISO_TO" >/dev/null || fail "effective date filter failed"
ok "Effective date range filters"

echo "=============================================="
echo "Baseline Filters Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
