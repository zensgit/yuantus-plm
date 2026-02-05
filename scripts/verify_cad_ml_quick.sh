#!/usr/bin/env bash
# =============================================================================
# CAD-ML quick regression: 2D preview + OCR title block
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_SAMPLE_FILE="${REPO_ROOT}/docs/samples/cad_ml_preview_sample.dxf"
SAMPLE_FILE="${4:-${CAD_PREVIEW_SAMPLE_FILE:-$DEFAULT_SAMPLE_FILE}}"

if [[ -z "$SAMPLE_FILE" ]]; then
  echo "ERROR: CAD_PREVIEW_SAMPLE_FILE is required (DWG/DXF)." >&2
  echo "Usage: CAD_PREVIEW_SAMPLE_FILE=/path/to/sample.dwg $0 [base_url] [tenant] [org]" >&2
  exit 2
fi
if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "ERROR: Sample file not found: $SAMPLE_FILE" >&2
  exit 2
fi

RUN_CAD_ML_DOCKER="${RUN_CAD_ML_DOCKER:-1}"
CAD_ML_API_PORT="${CAD_ML_API_PORT:-18000}"
CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-http://127.0.0.1:${CAD_ML_API_PORT}}"
export CAD_ML_BASE_URL
export YUANTUS_CAD_ML_BASE_URL="${YUANTUS_CAD_ML_BASE_URL:-${CAD_ML_BASE_URL}}"
export CAD_PREVIEW_SAMPLE_FILE="$SAMPLE_FILE"

CAD_ML_DOCKER_STARTED=0
cleanup_cad_ml_docker() {
  if [[ "${CAD_ML_DOCKER_STARTED:-0}" == "1" ]]; then
    echo ""
    echo "==> Stop cad-ml docker"
    "${REPO_ROOT}/scripts/stop_cad_ml_docker.sh" || true
  fi
}
trap cleanup_cad_ml_docker EXIT

if [[ "$RUN_CAD_ML_DOCKER" == "1" ]]; then
  if [[ ! -x "${REPO_ROOT}/scripts/run_cad_ml_docker.sh" || ! -x "${REPO_ROOT}/scripts/check_cad_ml_docker.sh" ]]; then
    echo "ERROR: cad-ml docker helpers not found (scripts/run_cad_ml_docker.sh)" >&2
    exit 2
  fi
  echo "==> Start cad-ml docker (RUN_CAD_ML_DOCKER=1)"
  "${REPO_ROOT}/scripts/run_cad_ml_docker.sh"
  "${REPO_ROOT}/scripts/check_cad_ml_docker.sh"
  CAD_ML_DOCKER_STARTED=1
fi

echo "==> CAD-ML quick regression (2D preview + OCR)"
"${REPO_ROOT}/scripts/verify_cad_preview_2d.sh" "$BASE_URL" "$TENANT" "$ORG"
"${REPO_ROOT}/scripts/verify_cad_ocr_titleblock.sh" "$BASE_URL" "$TENANT" "$ORG"
if [[ "${RUN_CAD_ML_METRICS:-0}" == "1" ]]; then
  echo "==> CAD-ML metrics smoke check"
  "${REPO_ROOT}/scripts/verify_cad_ml_metrics.sh"
else
  echo "SKIP: CAD-ML metrics (RUN_CAD_ML_METRICS=0)"
fi
echo "==> CAD-ML quick regression complete"
