#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
cd "$ROOT"

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Not a git repository: $ROOT" >&2
  exit 1
fi

baseline_switch_docs=(
  "docs/DEV_AND_VERIFICATION_BASELINE_CORRECTION_AUDIT_20260414.md"
  "docs/DEV_AND_VERIFICATION_BRANCH_MERGE_RISK_AUDIT_20260414.md"
  "docs/DEV_AND_VERIFICATION_MAINLINE_BASELINE_SWITCH_20260414.md"
  "docs/DEV_AND_VERIFICATION_MAINLINE_BASELINE_SWITCH_EXECUTION_20260414.md"
  "docs/DEV_AND_VERIFICATION_MAINLINE_BASELINE_SWITCH_PREVIEW_20260414.md"
  "docs/DEV_AND_VERIFICATION_PLM_WORKSPACE_MANUAL_REPLAY_PLAN_20260414.md"
  "docs/RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md"
  "scripts/print_mainline_baseline_switch_commands.sh"
)

cad_runtime_mainline=(
  "src/yuantus/cli.py"
  "src/yuantus/meta_engine/services/checkin_service.py"
  "src/yuantus/meta_engine/services/job_service.py"
  "src/yuantus/meta_engine/services/job_worker.py"
  "src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py"
  "src/yuantus/meta_engine/web/cad_router.py"
  "src/yuantus/meta_engine/web/file_router.py"
  "src/yuantus/meta_engine/tests/test_checkin_manager.py"
  "src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py"
  "src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py"
  "src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py"
  "src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py"
  "src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py"
  "src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py"
  "docs/DEV_AND_VERIFICATION_P1_CAD_CHECKIN_QUEUE_BINDING_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_CAD_CHECKIN_STATUS_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_FILE_CONVERSION_JOB_QUEUE_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_FILE_CONVERSION_SUMMARY_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_FILE_UPLOAD_PREVIEW_QUEUE_20260414.md"
)

cad_legacy_cleanup=(
  "src/yuantus/meta_engine/models/file.py"
  "src/yuantus/meta_engine/services/cad_converter_service.py"
  "scripts/audit_legacy_cad_conversion_jobs.py"
  "migrations/versions/a2b2c3d4e7a6_drop_legacy_cad_conversion_jobs.py"
  "src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py"
  "src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py"
  "docs/DESIGN_P1_CAD_LEGACY_CONVERSION_QUEUE_AUDIT_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_CAD_CONVERTER_QUEUE_SHIM_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_CONVERSION_QUEUE_AUDIT_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_DELETE_WINDOW_READINESS_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_MODEL_REMOVAL_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_TABLE_DROP_MIGRATION_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_CAD_LEGACY_QUEUE_FINAL_CLOSEOUT_20260414.md"
  "docs/RUNBOOK_CAD_LEGACY_CONVERSION_QUEUE_AUDIT.md"
)

docs_index_and_commit_prep=(
  "docs/DELIVERY_DOC_INDEX.md"
  "docs/RUNBOOK_P1_CAD_COMMIT_SEQUENCE_20260414.md"
  "docs/DEV_AND_VERIFICATION_P1_CAD_COMMIT_SEQUENCE_PREP_20260414.md"
  "scripts/print_p1_cad_commit_sequence_commands.sh"
)

print_slice() {
  local name="$1"
  local commit_message="$2"
  shift 2
  echo "## $name"
  printf "git add --"
  local f
  for f in "$@"; do
    printf " %q" "$f"
  done
  printf "\n"
  printf "git commit -m %q\n\n" "$commit_message"
}

print_slice "Slice 1: baseline-switch-docs" \
  "docs: add mainline baseline switch audit and runbook" \
  "${baseline_switch_docs[@]}"

print_slice "Slice 2: cad-runtime-mainline" \
  "feat(plm): move cad checkin and file conversion runtime to canonical queue" \
  "${cad_runtime_mainline[@]}"

print_slice "Slice 3: cad-legacy-cleanup" \
  "refactor(plm): remove legacy cad conversion queue runtime and add schema removal" \
  "${cad_legacy_cleanup[@]}"

print_slice "Slice 4: docs-index-and-commit-prep" \
  "docs: add p1 cad closeout index and commit prep guidance" \
  "${docs_index_and_commit_prep[@]}"

changed_files=()
while IFS= read -r path; do
  [[ -n "$path" ]] || continue
  changed_files+=("$path")
done < <(git status --porcelain | awk '{print substr($0,4)}' | sed '/^$/d' | sort -u)

covered=(
  "${baseline_switch_docs[@]}"
  "${cad_runtime_mainline[@]}"
  "${cad_legacy_cleanup[@]}"
  "${docs_index_and_commit_prep[@]}"
)

uncovered=()
for path in "${changed_files[@]}"; do
  found=0
  for covered_path in "${covered[@]}"; do
    if [[ "$covered_path" == "$path" ]]; then
      found=1
      break
    fi
  done
  if [[ $found -eq 0 ]]; then
    uncovered+=("$path")
  fi
done

echo "## Coverage"
echo "changed_files=${#changed_files[@]}"
echo "covered_files=${#covered[@]}"
echo "uncovered_files=${#uncovered[@]}"
if ((${#uncovered[@]} > 0)); then
  printf '%s\n' "${uncovered[@]}"
  exit 1
fi
