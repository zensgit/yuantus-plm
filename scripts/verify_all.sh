#!/usr/bin/env bash
# =============================================================================
# YuantusPLM End-to-End Regression Test Suite
# Master script that runs all verification scripts and reports summary
# =============================================================================
set -uo pipefail

# Configuration
BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"

# Export for child scripts
export CLI PY

# Colors (if terminal supports)
if [[ -t 1 ]]; then
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  YELLOW='\033[1;33m'
  NC='\033[0m' # No Color
else
  GREEN=''
  RED=''
  YELLOW=''
  NC=''
fi

# Results tracking
declare -A RESULTS
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0

echo "=============================================="
echo "YuantusPLM End-to-End Regression Suite"
echo "=============================================="
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "CLI: $CLI"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
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

  # Run the script and capture exit code without aborting the suite
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

has_openapi_path() {
  local path="$1"
  local found
  found="$(
    curl -s "$BASE_URL/openapi.json" \
      | "$PY" -c 'import sys,json; data=json.load(sys.stdin); print("1" if sys.argv[1] in data.get("paths", {}) else "0")' \
        "$path" 2>/dev/null || echo "0"
  )"
  [[ "$found" == "1" ]]
}

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------
echo "==> Pre-flight checks"

# Check CLI
if [[ ! -x "$CLI" ]]; then
  echo -e "${RED}ERROR${NC}: CLI not found at $CLI"
  echo "Set CLI=... to override"
  exit 2
fi
echo "CLI: OK"

# Check Python
if [[ ! -x "$PY" ]]; then
  echo -e "${RED}ERROR${NC}: Python not found at $PY"
  echo "Set PY=... to override"
  exit 2
fi
echo "Python: OK"

# Check API health
echo "Checking API health..."
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/health" \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" != "200" ]]; then
  echo -e "${RED}ERROR${NC}: API not reachable at $BASE_URL (HTTP $HTTP_CODE)"
  echo "Please start the server first:"
  echo "  docker compose up -d --build"
  echo "  OR"
  echo "  yuantus start --port 7910"
  exit 2
fi
echo "API Health: OK (HTTP $HTTP_CODE)"

echo ""
echo "Pre-flight checks passed. Starting tests..."

# -----------------------------------------------------------------------------
# Run test suites
# -----------------------------------------------------------------------------

# 1. Run H - Basic Health & Core APIs
run_test "Run H (Core APIs)" \
  "$SCRIPT_DIR/verify_run_h.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 2. S1 - Meta Schema + RBAC
run_test "S1 (Meta + RBAC)" \
  "$SCRIPT_DIR/verify_permissions.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 3. S3.1 - BOM Tree + Cycle Detection
run_test "S3.1 (BOM Tree)" \
  "$SCRIPT_DIR/verify_bom_tree.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 4. S3.2 - BOM Effectivity
run_test "S3.2 (BOM Effectivity)" \
  "$SCRIPT_DIR/verify_bom_effectivity.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 5. S3.3 - Version Semantics
run_test "S3.3 (Versions)" \
  "$SCRIPT_DIR/verify_versions.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 6. S5-A - CAD Pipeline S3
run_test "S5-A (CAD Pipeline S3)" \
  "$SCRIPT_DIR/verify_cad_pipeline_s3.sh" \
  "$BASE_URL" "$TENANT" "$ORG" || true

# 7. Where-Used (if exists)
if [[ -x "$SCRIPT_DIR/verify_where_used.sh" ]]; then
  run_test "Where-Used API" \
    "$SCRIPT_DIR/verify_where_used.sh" \
    "$BASE_URL" "$TENANT" "$ORG" || true
fi

# 8. BOM Compare (skip if endpoint not available)
if [[ -x "$SCRIPT_DIR/verify_bom_compare.sh" ]]; then
  if has_openapi_path "/api/v1/bom/compare"; then
    run_test "BOM Compare" \
      "$SCRIPT_DIR/verify_bom_compare.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "BOM Compare" "endpoint not available"
  fi
fi

# 9. BOM Substitutes (skip if endpoint not available)
if [[ -x "$SCRIPT_DIR/verify_substitutes.sh" ]]; then
  if has_openapi_path "/api/v1/bom/{bom_line_id}/substitutes"; then
    run_test "BOM Substitutes" \
      "$SCRIPT_DIR/verify_substitutes.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "BOM Substitutes" "endpoint not available"
  fi
fi

# 10. Version-File Binding (skip if endpoint not available)
if [[ -x "$SCRIPT_DIR/verify_version_files.sh" ]]; then
  if has_openapi_path "/api/v1/versions/{version_id}/files"; then
    run_test "Version-File Binding" \
      "$SCRIPT_DIR/verify_version_files.sh" \
      "$BASE_URL" "$TENANT" "$ORG" || true
  else
    skip_test "Version-File Binding" "endpoint not available"
  fi
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "REGRESSION TEST SUMMARY"
echo "=============================================="
echo ""

# Print results table
printf "%-25s %s\n" "Test Suite" "Result"
printf "%-25s %s\n" "-------------------------" "------"

for name in "Run H (Core APIs)" "S1 (Meta + RBAC)" "S3.1 (BOM Tree)" "S3.2 (BOM Effectivity)" "S3.3 (Versions)" "S5-A (CAD Pipeline S3)" "Where-Used API" "BOM Compare" "BOM Substitutes" "Version-File Binding"; do
  result="${RESULTS[$name]:-N/A}"
  case "$result" in
    PASS) printf "%-25s ${GREEN}%s${NC}\n" "$name" "$result" ;;
    FAIL) printf "%-25s ${RED}%s${NC}\n" "$name" "$result" ;;
    SKIP) printf "%-25s ${YELLOW}%s${NC}\n" "$name" "$result" ;;
    *)    printf "%-25s %s\n" "$name" "$result" ;;
  esac
done

echo ""
echo "----------------------------------------------"
printf "PASS: ${GREEN}%d${NC}  FAIL: ${RED}%d${NC}  SKIP: ${YELLOW}%d${NC}\n" "$TOTAL_PASS" "$TOTAL_FAIL" "$TOTAL_SKIP"
echo "----------------------------------------------"

# Exit with appropriate code
if [[ $TOTAL_FAIL -gt 0 ]]; then
  echo ""
  echo -e "${RED}REGRESSION FAILED${NC}"
  exit 1
else
  echo ""
  echo -e "${GREEN}ALL TESTS PASSED${NC}"
  exit 0
fi
