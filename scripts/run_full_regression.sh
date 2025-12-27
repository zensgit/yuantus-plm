#!/usr/bin/env bash
# =============================================================================
# Full regression runner with all optional CAD/extractor/provisioning checks.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

DEFAULT_COVERAGE_DIR="/Users/huazhou/Downloads/训练图纸/训练图纸"
DEFAULT_SAMPLE_DWG="/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg"
DEFAULT_SAMPLE_ZHONGWANG="/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg"
DEFAULT_SAMPLE_STEP="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp"
DEFAULT_SAMPLE_PRT="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt"

CAD_CONNECTOR_COVERAGE_DIR="${CAD_CONNECTOR_COVERAGE_DIR:-$DEFAULT_COVERAGE_DIR}"
CAD_SAMPLE_DWG="${CAD_SAMPLE_DWG:-$DEFAULT_SAMPLE_DWG}"
CAD_SAMPLE_STEP="${CAD_SAMPLE_STEP:-$DEFAULT_SAMPLE_STEP}"
CAD_SAMPLE_PRT="${CAD_SAMPLE_PRT:-$DEFAULT_SAMPLE_PRT}"
CAD_SAMPLE_HAOCHEN_DWG="${CAD_SAMPLE_HAOCHEN_DWG:-$DEFAULT_SAMPLE_DWG}"
CAD_SAMPLE_ZHONGWANG_DWG="${CAD_SAMPLE_ZHONGWANG_DWG:-$DEFAULT_SAMPLE_ZHONGWANG}"
CAD_EXTRACTOR_BASE_URL="${CAD_EXTRACTOR_BASE_URL:-http://localhost:8200}"
CAD_EXTRACTOR_SAMPLE_FILE="${CAD_EXTRACTOR_SAMPLE_FILE:-$DEFAULT_SAMPLE_DWG}"
CAD_EXTRACTOR_EXPECT_KEY="${CAD_EXTRACTOR_EXPECT_KEY:-part_number}"
CAD_EXTRACTOR_EXPECT_VALUE="${CAD_EXTRACTOR_EXPECT_VALUE:-J2824002-06}"

require_dir() {
  local path="$1"
  local label="$2"
  if [[ ! -d "$path" ]]; then
    echo "Missing $label directory: $path" >&2
    return 1
  fi
}

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "Missing $label file: $path" >&2
    return 1
  fi
}

missing=0
require_dir "$CAD_CONNECTOR_COVERAGE_DIR" "CAD_CONNECTOR_COVERAGE_DIR" || missing=1
require_file "$CAD_SAMPLE_DWG" "CAD_SAMPLE_DWG" || missing=1
require_file "$CAD_SAMPLE_STEP" "CAD_SAMPLE_STEP" || missing=1
require_file "$CAD_SAMPLE_PRT" "CAD_SAMPLE_PRT" || missing=1
require_file "$CAD_SAMPLE_HAOCHEN_DWG" "CAD_SAMPLE_HAOCHEN_DWG" || missing=1
require_file "$CAD_SAMPLE_ZHONGWANG_DWG" "CAD_SAMPLE_ZHONGWANG_DWG" || missing=1
require_file "$CAD_EXTRACTOR_SAMPLE_FILE" "CAD_EXTRACTOR_SAMPLE_FILE" || missing=1

if [[ "$missing" -ne 0 ]]; then
  echo "Set the missing paths via env vars before re-running." >&2
  exit 2
fi

if ! curl -fsS "${CAD_EXTRACTOR_BASE_URL%/}/health" >/dev/null 2>&1; then
  echo "CAD extractor not reachable at ${CAD_EXTRACTOR_BASE_URL%/}/health" >&2
  exit 2
fi

export RUN_CAD_REAL_CONNECTORS_2D=1
export RUN_CAD_CONNECTOR_COVERAGE_2D=1
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_CAD_REAL_SAMPLES=1
export RUN_TENANT_PROVISIONING=1

export CAD_CONNECTOR_COVERAGE_DIR
export CAD_SAMPLE_DWG
export CAD_SAMPLE_STEP
export CAD_SAMPLE_PRT
export CAD_SAMPLE_HAOCHEN_DWG
export CAD_SAMPLE_ZHONGWANG_DWG
export CAD_EXTRACTOR_BASE_URL
export CAD_EXTRACTOR_SAMPLE_FILE
export CAD_EXTRACTOR_EXPECT_KEY
export CAD_EXTRACTOR_EXPECT_VALUE

"$SCRIPT_DIR/verify_all.sh" "$BASE_URL" "$TENANT" "$ORG"
