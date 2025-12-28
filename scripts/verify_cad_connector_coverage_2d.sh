#!/usr/bin/env bash
# =============================================================================
# CAD 2D Connector Coverage (offline)
# Generates coverage reports for Haochen/Zhongwang connectors using local files.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_PY="$REPO_ROOT/.venv/bin/python"
if [[ -x "$DEFAULT_PY" ]]; then
  PY="${PY:-$DEFAULT_PY}"
else
  PY="${PY:-python3}"
fi
PYTHONPATH="${PYTHONPATH:-$REPO_ROOT/src}"
export PYTHONPATH

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Missing python at $PY (set PY=...)" >&2
  exit 2
fi

COVERAGE_SCRIPT="$SCRIPT_DIR/collect_cad_extractor_coverage.py"
if [[ ! -f "$COVERAGE_SCRIPT" ]]; then
  echo "Missing coverage script at $COVERAGE_SCRIPT" >&2
  exit 2
fi

CAD_CONNECTOR_COVERAGE_DIR="${CAD_CONNECTOR_COVERAGE_DIR:-}"
if [[ -z "$CAD_CONNECTOR_COVERAGE_DIR" || ! -d "$CAD_CONNECTOR_COVERAGE_DIR" ]]; then
  echo "Missing CAD_CONNECTOR_COVERAGE_DIR (set to a directory with DWG files)." >&2
  exit 2
fi

CAD_CONNECTOR_COVERAGE_EXTENSIONS="${CAD_CONNECTOR_COVERAGE_EXTENSIONS:-dwg}"
CAD_CONNECTOR_COVERAGE_MAX_FILES="${CAD_CONNECTOR_COVERAGE_MAX_FILES:-0}"
CAD_CONNECTOR_COVERAGE_FORCE_UNIQUE="${CAD_CONNECTOR_COVERAGE_FORCE_UNIQUE:-0}"
CAD_CONNECTOR_COVERAGE_OUT_HAOCHEN="${CAD_CONNECTOR_COVERAGE_OUT_HAOCHEN:-$REPO_ROOT/docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md}"
CAD_CONNECTOR_COVERAGE_OUT_ZHONGWANG="${CAD_CONNECTOR_COVERAGE_OUT_ZHONGWANG:-$REPO_ROOT/docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md}"

COMMON_ARGS=(
  --offline
  --dir "$CAD_CONNECTOR_COVERAGE_DIR"
  --extensions "$CAD_CONNECTOR_COVERAGE_EXTENSIONS"
)

if [[ "$CAD_CONNECTOR_COVERAGE_MAX_FILES" != "0" ]]; then
  COMMON_ARGS+=(--max-files "$CAD_CONNECTOR_COVERAGE_MAX_FILES")
fi
if [[ "$CAD_CONNECTOR_COVERAGE_FORCE_UNIQUE" == "1" ]]; then
  COMMON_ARGS+=(--force-unique)
fi

echo "=============================================="
echo "CAD 2D Connector Coverage (offline)"
echo "Dir: $CAD_CONNECTOR_COVERAGE_DIR"
echo "Extensions: $CAD_CONNECTOR_COVERAGE_EXTENSIONS"
echo "Max files: $CAD_CONNECTOR_COVERAGE_MAX_FILES"
echo "Force unique: $CAD_CONNECTOR_COVERAGE_FORCE_UNIQUE"
echo "=============================================="

"$PY" "$COVERAGE_SCRIPT" \
  "${COMMON_ARGS[@]}" \
  --cad-format HAOCHEN \
  --cad-connector-id haochencad \
  --report-title "CAD 2D Connector Coverage Report (Haochen, Offline)" \
  --output "$CAD_CONNECTOR_COVERAGE_OUT_HAOCHEN"

"$PY" "$COVERAGE_SCRIPT" \
  "${COMMON_ARGS[@]}" \
  --cad-format ZHONGWANG \
  --cad-connector-id zhongwangcad \
  --report-title "CAD 2D Connector Coverage Report (Zhongwang, Offline)" \
  --output "$CAD_CONNECTOR_COVERAGE_OUT_ZHONGWANG"

echo "=============================================="
echo "CAD 2D Connector Coverage Complete"
echo "Haochen: $CAD_CONNECTOR_COVERAGE_OUT_HAOCHEN"
echo "Zhongwang: $CAD_CONNECTOR_COVERAGE_OUT_ZHONGWANG"
echo "=============================================="
