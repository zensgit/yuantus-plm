#!/usr/bin/env bash
# =============================================================================
# YuantusPLM Local Regression Suite (TestClient)
# Runs local-only verification scripts without binding ports or Docker.
# =============================================================================
set -uo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"

export CLI PY
export LOCAL_TESTCLIENT=1

if [[ -z "${YUANTUS_DATABASE_URL:-}" ]]; then
  export YUANTUS_DATABASE_URL="sqlite:///yuantus_local_verify.db"
fi

if [[ -t 1 ]]; then
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  YELLOW='\033[1;33m'
  NC='\033[0m'
else
  GREEN=''
  RED=''
  YELLOW=''
  NC=''
fi

declare -A RESULTS
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0

echo "=============================================="
echo "YuantusPLM Local Regression Suite"
echo "=============================================="
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "CLI: $CLI"
echo "PY: $PY"
echo "YUANTUS_DATABASE_URL: ${YUANTUS_DATABASE_URL}"
echo "LOCAL_TESTCLIENT: ${LOCAL_TESTCLIENT}"
echo "=============================================="
echo ""

run_test() {
  local name="$1"
  local script="$2"
  shift 2
  local args=("$@")

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Running: $name"
  echo "Script: $script"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if [[ ! -x "$script" ]]; then
    echo -e "${YELLOW}SKIP${NC}: Script not found or not executable"
    RESULTS["$name"]="SKIP"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
    return 2
  fi

  "$script" "${args[@]}" 2>&1
  local exit_code=$?

  if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}PASS${NC}: $name"
    RESULTS["$name"]="PASS"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    echo -e "${RED}FAIL${NC}: $name (exit code: $exit_code)"
    RESULTS["$name"]="FAIL"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi

  return $exit_code
}

skip_test() {
  local name="$1"
  local reason="$2"
  echo -e "${YELLOW}SKIP${NC}: $name ($reason)"
  RESULTS["$name"]="SKIP"
  TOTAL_SKIP=$((TOTAL_SKIP + 1))
}

run_test "Relationship ItemType Expand" \
  "$SCRIPT_DIR/verify_relationship_itemtype_expand.sh" || true

run_test "RelationshipType Seeding" \
  "$SCRIPT_DIR/verify_relationship_type_seeding.sh" || true

run_test "Relationship Legacy Usage" \
  "$SCRIPT_DIR/verify_relationship_legacy_usage.sh" || true

run_test "Where-Used Line Schema" \
  "$SCRIPT_DIR/verify_where_used_schema.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

run_test "UI Where-Used" \
  "$SCRIPT_DIR/verify_where_used_ui.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

run_test "UI Product Summary" \
  "$SCRIPT_DIR/verify_product_ui.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

run_test "UI Docs ECO Summary" \
  "$SCRIPT_DIR/verify_docs_eco_ui.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

echo ""
echo "=============================================="
echo "Local Regression Summary"
echo "PASS: $TOTAL_PASS, FAIL: $TOTAL_FAIL, SKIP: $TOTAL_SKIP"
echo "=============================================="

for name in "${!RESULTS[@]}"; do
  printf "%-35s : %s\n" "$name" "${RESULTS[$name]}"
done

if [[ $TOTAL_FAIL -gt 0 ]]; then
  exit 1
fi
