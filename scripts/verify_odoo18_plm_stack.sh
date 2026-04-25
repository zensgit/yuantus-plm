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

PYTEST_CMD=()
if [[ -n "${PYTEST_BIN:-}" ]]; then
  PYTEST_CMD=("${PYTEST_BIN}")
else
  PYTEST_CMD=("${PY_BIN}" -m pytest)
fi

usage() {
  cat <<'EOF'
Usage: scripts/verify_odoo18_plm_stack.sh [smoke|full]

Modes:
  smoke  Run the focused Odoo18 PLM smoke set.
  full   Run the broader Odoo18 PLM regression set. This is the default.

Environment:
  PY_BIN          Python executable. Defaults to .venv/bin/python when present.
  PYTEST_BIN      Optional pytest executable override.
  PYTHONPYCACHEPREFIX
                  Optional pycache output directory. Defaults to /tmp/yuantus-pyc.
EOF
}

if [[ "$#" -gt 1 ]]; then
  usage >&2
  exit 2
fi

case "$MODE" in
  -h|--help)
    usage
    exit 0
    ;;
esac

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
  "src/yuantus/meta_engine/box/__init__.py"
  "src/yuantus/meta_engine/box/models.py"
  "src/yuantus/meta_engine/box/service.py"
  "src/yuantus/meta_engine/web/box_aging_router.py"
  "src/yuantus/meta_engine/web/box_analytics_router.py"
  "src/yuantus/meta_engine/web/box_capacity_router.py"
  "src/yuantus/meta_engine/web/box_core_router.py"
  "src/yuantus/meta_engine/web/box_custody_router.py"
  "src/yuantus/meta_engine/web/box_ops_router.py"
  "src/yuantus/meta_engine/web/box_policy_router.py"
  "src/yuantus/meta_engine/web/box_reconciliation_router.py"
  "src/yuantus/meta_engine/web/box_router.py"
  "src/yuantus/meta_engine/web/box_traceability_router.py"
  "src/yuantus/meta_engine/web/box_turnover_router.py"
  "src/yuantus/meta_engine/document_sync/__init__.py"
  "src/yuantus/meta_engine/document_sync/models.py"
  "src/yuantus/meta_engine/document_sync/service.py"
  "src/yuantus/meta_engine/web/document_sync_analytics_router.py"
  "src/yuantus/meta_engine/web/document_sync_core_router.py"
  "src/yuantus/meta_engine/web/document_sync_drift_router.py"
  "src/yuantus/meta_engine/web/document_sync_freshness_router.py"
  "src/yuantus/meta_engine/web/document_sync_lineage_router.py"
  "src/yuantus/meta_engine/web/document_sync_reconciliation_router.py"
  "src/yuantus/meta_engine/web/document_sync_replay_audit_router.py"
  "src/yuantus/meta_engine/web/document_sync_retention_router.py"
  "src/yuantus/meta_engine/web/document_sync_router.py"
  "src/yuantus/meta_engine/cutted_parts/__init__.py"
  "src/yuantus/meta_engine/cutted_parts/models.py"
  "src/yuantus/meta_engine/cutted_parts/service.py"
  "src/yuantus/meta_engine/web/cutted_parts_alerts_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_analytics_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_benchmark_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_bottlenecks_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_core_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_scenarios_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_thresholds_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_throughput_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_utilization_router.py"
  "src/yuantus/meta_engine/web/cutted_parts_variance_router.py"
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
  "src/yuantus/meta_engine/tests/test_box_router.py"
  "src/yuantus/meta_engine/tests/test_document_sync_router.py"
  "src/yuantus/meta_engine/tests/test_cutted_parts_router.py"
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
  "src/yuantus/meta_engine/tests/test_box_service.py"
  "src/yuantus/meta_engine/tests/test_box_router.py"
  "src/yuantus/meta_engine/tests/test_document_sync_service.py"
  "src/yuantus/meta_engine/tests/test_document_sync_router.py"
  "src/yuantus/meta_engine/tests/test_cutted_parts_service.py"
  "src/yuantus/meta_engine/tests/test_cutted_parts_router.py"
)

case "$MODE" in
  smoke)
    selected_tests=("${smoke_tests[@]}")
    ;;
  full)
    selected_tests=("${full_tests[@]}")
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

cd "$REPO_ROOT"

# Router decomposition is still active across Odoo18 PLM domains. Keep the
# syntax gate complete without hand-maintaining every split router file.
while IFS= read -r router_file; do
  compile_files+=("$router_file")
done < <(find "src/yuantus/meta_engine/web" -maxdepth 1 -type f -name "*_router.py" | sort)

deduped_compile_files=()
seen_compile_files=$'\n'
for compile_file in "${compile_files[@]}"; do
  if [[ "$seen_compile_files" != *$'\n'"$compile_file"$'\n'* ]]; then
    deduped_compile_files+=("$compile_file")
    seen_compile_files+="$compile_file"$'\n'
  fi
done
compile_files=("${deduped_compile_files[@]}")

echo "[verify_odoo18_plm_stack] mode=${MODE}"
echo "[verify_odoo18_plm_stack] py_compile"
"$PY_BIN" -m py_compile "${compile_files[@]}"

echo "[verify_odoo18_plm_stack] pytest"
"${PYTEST_CMD[@]}" -q "${selected_tests[@]}"

echo "[verify_odoo18_plm_stack] PASS"
