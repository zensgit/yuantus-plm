#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-full}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PY_BIN="${PY_BIN:-}"
if [[ -z "$PY_BIN" ]]; then
  if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PY_BIN="${REPO_ROOT}/.venv/bin/python"
  else
    PY_BIN="python3"
  fi
fi

PYTEST_BIN="${PYTEST_BIN:-}"
if [[ -z "$PYTEST_BIN" ]]; then
  if [[ -x "${REPO_ROOT}/.venv/bin/pytest" ]]; then
    PYTEST_BIN="${REPO_ROOT}/.venv/bin/pytest"
  else
    PYTEST_BIN="pytest"
  fi
fi

export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/yuantus-pyc}"

compile_files=(
  "src/yuantus/api/app.py"
  "src/yuantus/meta_engine/services/cad_converter_service.py"
  "src/yuantus/meta_engine/web/file_router.py"
  "src/yuantus/meta_engine/approvals/__init__.py"
  "src/yuantus/meta_engine/approvals/models.py"
  "src/yuantus/meta_engine/approvals/service.py"
  "src/yuantus/meta_engine/web/approvals_router.py"
  "src/yuantus/meta_engine/quality/models.py"
  "src/yuantus/meta_engine/quality/analytics_service.py"
  "src/yuantus/meta_engine/quality/service.py"
  "src/yuantus/meta_engine/quality/spc_service.py"
  "src/yuantus/meta_engine/web/quality_analytics_router.py"
  "src/yuantus/meta_engine/web/quality_router.py"
  "src/yuantus/meta_engine/maintenance/models.py"
  "src/yuantus/meta_engine/maintenance/service.py"
  "src/yuantus/meta_engine/web/maintenance_router.py"
  "src/yuantus/meta_engine/locale/service.py"
  "src/yuantus/meta_engine/report_locale/service.py"
  "src/yuantus/meta_engine/web/locale_router.py"
  "src/yuantus/meta_engine/subcontracting/models.py"
  "src/yuantus/meta_engine/subcontracting/service.py"
  "src/yuantus/meta_engine/web/subcontracting_router.py"
  "src/yuantus/meta_engine/web/bom_router.py"
)

smoke_tests=(
  "src/yuantus/meta_engine/tests/test_file_viewer_readiness.py"
  "src/yuantus/meta_engine/tests/test_quality_analytics_router.py"
  "src/yuantus/meta_engine/tests/test_quality_router.py"
  "src/yuantus/meta_engine/tests/test_maintenance_router.py"
  "src/yuantus/meta_engine/tests/test_locale_router.py"
  "src/yuantus/meta_engine/tests/test_subcontracting_router.py"
  "src/yuantus/meta_engine/tests/test_approvals_router.py"
)

full_tests=(
  "src/yuantus/meta_engine/tests/test_bom_summarized_router.py"
  "src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py"
  "src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py"
  "src/yuantus/meta_engine/tests/test_bom_delta_preview.py"
  "src/yuantus/meta_engine/tests/test_bom_delta_router.py"
  "src/yuantus/meta_engine/tests/test_quality_service.py"
  "src/yuantus/meta_engine/tests/test_quality_analytics_service.py"
  "src/yuantus/meta_engine/tests/test_quality_analytics_router.py"
  "src/yuantus/meta_engine/tests/test_quality_spc_service.py"
  "src/yuantus/meta_engine/tests/test_quality_router.py"
  "src/yuantus/meta_engine/tests/test_maintenance_service.py"
  "src/yuantus/meta_engine/tests/test_maintenance_router.py"
  "src/yuantus/meta_engine/tests/test_locale_service.py"
  "src/yuantus/meta_engine/tests/test_report_locale_service.py"
  "src/yuantus/meta_engine/tests/test_locale_router.py"
  "src/yuantus/meta_engine/tests/test_subcontracting_service.py"
  "src/yuantus/meta_engine/tests/test_subcontracting_router.py"
  "src/yuantus/meta_engine/tests/test_file_viewer_readiness.py"
  "src/yuantus/meta_engine/tests/test_approvals_service.py"
  "src/yuantus/meta_engine/tests/test_approvals_router.py"
)

case "$MODE" in
  smoke)
    selected_tests=("${smoke_tests[@]}")
    ;;
  full)
    selected_tests=("${full_tests[@]}")
    ;;
  *)
    echo "Usage: $0 [smoke|full]" >&2
    exit 2
    ;;
esac

cd "$REPO_ROOT"

echo "[verify_odoo18_plm_stack] mode=${MODE}"
echo "[verify_odoo18_plm_stack] py_compile"
"$PY_BIN" -m py_compile "${compile_files[@]}"

echo "[verify_odoo18_plm_stack] pytest"
"$PYTEST_BIN" -q "${selected_tests[@]}"

echo "[verify_odoo18_plm_stack] PASS"
