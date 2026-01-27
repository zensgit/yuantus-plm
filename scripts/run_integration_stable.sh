#!/usr/bin/env bash
# =============================================================================
# Integration stability runner.
# Auto-enables optional suites based on environment availability.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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
CAD_EXTRACTOR_SAMPLE_FILE="${CAD_EXTRACTOR_SAMPLE_FILE:-$DEFAULT_SAMPLE_DWG}"
CADGF_PREVIEW_SAMPLE_FILE="${CADGF_PREVIEW_SAMPLE_FILE:-$DEFAULT_SAMPLE_DWG}"

CAD_EXTRACTOR_BASE_URL="${CAD_EXTRACTOR_BASE_URL:-http://localhost:8200}"
CAD_CONNECTOR_BASE_URL="${CAD_CONNECTOR_BASE_URL:-http://localhost:8300}"

load_server_env() {
  local pid_file="${REPO_ROOT}/yuantus.pid"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && ps -p "$pid" >/dev/null 2>&1; then
      local tokens
      tokens="$(ps eww -p "$pid" -o command= | tr ' ' '\n' | grep '^YUANTUS_' || true)"
      while IFS= read -r token; do
        [[ -z "$token" ]] && continue
        local key="${token%%=*}"
        local value="${token#*=}"
        if [[ -z "${!key:-}" ]]; then
          export "${key}=${value}"
        fi
      done <<< "$tokens"
    fi
  fi
}

url_ok() {
  local url="$1"
  curl -fsS "$url" >/dev/null 2>&1
}

set_default() {
  local var="$1"
  local value="$2"
  if [[ -z "${!var+x}" ]]; then
    export "$var=$value"
  fi
}

load_server_env

ENABLED=()
DISABLED=()

set_default RUN_UI_AGG 1
ENABLED+=("RUN_UI_AGG")

set_default RUN_TENANT_PROVISIONING 1
ENABLED+=("RUN_TENANT_PROVISIONING")

set_default RUN_OPS_S8 1
ENABLED+=("RUN_OPS_S8")

set_default RUN_CAD_EXTRACTOR_STUB 1
ENABLED+=("RUN_CAD_EXTRACTOR_STUB")

set_default RUN_CAD_AUTO_PART 1
ENABLED+=("RUN_CAD_AUTO_PART")

if [[ -f "$CAD_SAMPLE_HAOCHEN_DWG" && -f "$CAD_SAMPLE_ZHONGWANG_DWG" ]]; then
  set_default RUN_CAD_REAL_CONNECTORS_2D 1
  ENABLED+=("RUN_CAD_REAL_CONNECTORS_2D")
else
  set_default RUN_CAD_REAL_CONNECTORS_2D 0
  DISABLED+=("RUN_CAD_REAL_CONNECTORS_2D (missing DWG samples)")
fi

if [[ -d "$CAD_CONNECTOR_COVERAGE_DIR" ]]; then
  set_default RUN_CAD_CONNECTOR_COVERAGE_2D 1
  ENABLED+=("RUN_CAD_CONNECTOR_COVERAGE_2D")
else
  set_default RUN_CAD_CONNECTOR_COVERAGE_2D 0
  DISABLED+=("RUN_CAD_CONNECTOR_COVERAGE_2D (missing coverage dir)")
fi

if url_ok "${CAD_EXTRACTOR_BASE_URL%/}/health"; then
  set_default RUN_CAD_EXTRACTOR_EXTERNAL 1
  ENABLED+=("RUN_CAD_EXTRACTOR_EXTERNAL")
  if [[ -f "$CAD_EXTRACTOR_SAMPLE_FILE" ]]; then
    export CAD_EXTRACTOR_SAMPLE_FILE
  fi
else
  set_default RUN_CAD_EXTRACTOR_EXTERNAL 0
  DISABLED+=("RUN_CAD_EXTRACTOR_EXTERNAL (extractor not reachable)")
fi

if command -v docker >/dev/null 2>&1; then
  set_default RUN_CAD_EXTRACTOR_SERVICE 1
  ENABLED+=("RUN_CAD_EXTRACTOR_SERVICE")
else
  set_default RUN_CAD_EXTRACTOR_SERVICE 0
  DISABLED+=("RUN_CAD_EXTRACTOR_SERVICE (docker missing)")
fi

if [[ -f "$CAD_SAMPLE_DWG" && -f "$CAD_SAMPLE_STEP" && -f "$CAD_SAMPLE_PRT" ]]; then
  if url_ok "${CAD_EXTRACTOR_BASE_URL%/}/health"; then
    set_default RUN_CAD_REAL_SAMPLES 1
    ENABLED+=("RUN_CAD_REAL_SAMPLES")
  else
    set_default RUN_CAD_REAL_SAMPLES 0
    DISABLED+=("RUN_CAD_REAL_SAMPLES (extractor not reachable)")
  fi
else
  set_default RUN_CAD_REAL_SAMPLES 0
  DISABLED+=("RUN_CAD_REAL_SAMPLES (missing DWG/STEP/PRT samples)")
fi

if [[ -n "${YUANTUS_CADGF_ROUTER_BASE_URL:-}" || -n "${YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL:-}" ]]; then
  if [[ -f "$CADGF_PREVIEW_SAMPLE_FILE" ]]; then
    set_default RUN_CADGF_PREVIEW_ONLINE 1
    ENABLED+=("RUN_CADGF_PREVIEW_ONLINE")
    export CADGF_PREVIEW_SAMPLE_FILE
  else
    set_default RUN_CADGF_PREVIEW_ONLINE 0
    DISABLED+=("RUN_CADGF_PREVIEW_ONLINE (missing CADGF_PREVIEW_SAMPLE_FILE)")
  fi
else
  set_default RUN_CADGF_PREVIEW_ONLINE 0
  DISABLED+=("RUN_CADGF_PREVIEW_ONLINE (CADGF router not configured)")
fi

if url_ok "${CAD_CONNECTOR_BASE_URL%/}/health"; then
  export CAD_CONNECTOR_BASE_URL
fi

printf "==============================================\n"
printf "Integration Stability Runner\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "CAD_EXTRACTOR_BASE_URL: %s\n" "$CAD_EXTRACTOR_BASE_URL"
printf "CAD_CONNECTOR_BASE_URL: %s\n" "$CAD_CONNECTOR_BASE_URL"
printf "CAD_CONNECTOR_COVERAGE_DIR: %s\n" "$CAD_CONNECTOR_COVERAGE_DIR"
printf "CAD_SAMPLE_DWG: %s\n" "$CAD_SAMPLE_DWG"
printf "CAD_SAMPLE_STEP: %s\n" "$CAD_SAMPLE_STEP"
printf "CAD_SAMPLE_PRT: %s\n" "$CAD_SAMPLE_PRT"
if [[ -n "${YUANTUS_CADGF_ROUTER_BASE_URL:-}" ]]; then
  printf "YUANTUS_CADGF_ROUTER_BASE_URL: %s\n" "$YUANTUS_CADGF_ROUTER_BASE_URL"
fi
if [[ -n "${YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL:-}" ]]; then
  printf "YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL: %s\n" "$YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL"
fi
printf "==============================================\n"

if [[ "${#ENABLED[@]}" -gt 0 ]]; then
  printf "Enabled: %s\n" "${ENABLED[*]}"
fi
if [[ "${#DISABLED[@]}" -gt 0 ]]; then
  printf "Disabled: %s\n" "${DISABLED[*]}"
fi
printf "==============================================\n\n"

export CAD_CONNECTOR_COVERAGE_DIR
export CAD_SAMPLE_DWG
export CAD_SAMPLE_STEP
export CAD_SAMPLE_PRT
export CAD_SAMPLE_HAOCHEN_DWG
export CAD_SAMPLE_ZHONGWANG_DWG
export CAD_EXTRACTOR_BASE_URL

"$SCRIPT_DIR/verify_all.sh" "$BASE_URL" "$TENANT" "$ORG"
