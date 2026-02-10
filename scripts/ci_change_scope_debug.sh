#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/ci_change_scope_debug.sh [options]

Options:
  --base-ref <ref>        Base ref to diff against (default: origin/main)
  --head-ref <ref>        Head ref to diff (default: HEAD)
  --no-merge-base         Use base-ref directly instead of merge-base(base-ref, head-ref)

  --event <name>          Simulate event for regression rules: pull_request|push (default: pull_request)

  --force-full            Simulate CI label override `ci:full` (forces all CI flags true)
  --force-regression      Simulate regression label override `regression:force`
  --force-cadgf           Simulate regression label override `cadgf:force`

  --show-files            Print changed files (first N)
  --max-files <n>         Max changed files to print when --show-files (default: 50)

  -h, --help              Show help

Examples:
  scripts/ci_change_scope_debug.sh
  scripts/ci_change_scope_debug.sh --base-ref origin/main --head-ref HEAD --show-files
  scripts/ci_change_scope_debug.sh --event push --no-merge-base --base-ref HEAD~1 --head-ref HEAD
  scripts/ci_change_scope_debug.sh --force-full
  scripts/ci_change_scope_debug.sh --force-regression
EOF
}

BASE_REF="origin/main"
HEAD_REF="HEAD"
USE_MERGE_BASE="true"
EVENT="pull_request"
FORCE_FULL="false"
FORCE_REGRESSION="false"
FORCE_CADGF="false"
SHOW_FILES="false"
MAX_FILES="50"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --base-ref)
      BASE_REF="$2"; shift 2 ;;
    --head-ref)
      HEAD_REF="$2"; shift 2 ;;
    --no-merge-base)
      USE_MERGE_BASE="false"; shift ;;
    --event)
      EVENT="$2"; shift 2 ;;
    --force-full)
      FORCE_FULL="true"; shift ;;
    --force-regression)
      FORCE_REGRESSION="true"; shift ;;
    --force-cadgf)
      FORCE_CADGF="true"; shift ;;
    --show-files)
      SHOW_FILES="true"; shift ;;
    --max-files)
      MAX_FILES="$2"; shift 2 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is required" >&2
  exit 1
fi

if [[ "${EVENT}" != "pull_request" && "${EVENT}" != "push" ]]; then
  echo "ERROR: --event must be pull_request or push (got: ${EVENT})" >&2
  exit 2
fi

head_sha="$(git rev-parse --verify "${HEAD_REF}")"
if [[ "${USE_MERGE_BASE}" == "true" ]]; then
  base_sha="$(git merge-base "${BASE_REF}" "${HEAD_REF}")"
else
  base_sha="$(git rev-parse --verify "${BASE_REF}")"
fi

changed="$(mktemp)"
trap 'rm -f "${changed}" >/dev/null 2>&1 || true' EXIT

git diff --name-only "${base_sha}" "${head_sha}" > "${changed}"
changed_count="$(wc -l < "${changed}" | tr -d ' ')"

if [[ "${SHOW_FILES}" == "true" ]]; then
  echo "Changed files (first ${MAX_FILES}/${changed_count}):"
  head -n "${MAX_FILES}" "${changed}" || true
  if [[ "${changed_count}" -gt "${MAX_FILES}" ]]; then
    echo "... (truncated)"
  fi
  echo ""
fi

echo "## CI Change Scope (local debug)"
echo ""
echo "- base_sha: ${base_sha}"
echo "- head_sha: ${head_sha}"
echo "- changed_files: ${changed_count}"
echo "- force_full: ${FORCE_FULL}"
echo ""

run_plugin_tests="false"
run_playwright="false"
run_contracts="false"
reason_plugin_tests=""
reason_playwright=""
reason_contracts=""

while IFS= read -r f; do
  [[ -z "${f}" ]] && continue

  case "${f}" in
    .github/workflows/ci.yml|pyproject.toml|requirements.lock|alembic.ini)
      run_plugin_tests="true"
      run_playwright="true"
      run_contracts="true"
      reason_plugin_tests="${reason_plugin_tests:-matched core inputs: ${f}}"
      reason_playwright="${reason_playwright:-matched core inputs: ${f}}"
      reason_contracts="${reason_contracts:-matched core inputs: ${f}}"
      break
      ;;
    .github/workflows/*.yml|.github/workflows/*.yaml|configs/perf_gate.json)
      run_contracts="true"
      reason_contracts="${reason_contracts:-matched workflow/perf config: ${f}}"
      ;;
    scripts/perf_*.py|scripts/perf_*.sh)
      run_contracts="true"
      reason_contracts="${reason_contracts:-matched perf script: ${f}}"
      ;;
    scripts/*.sh|scripts/*.py)
      run_contracts="true"
      reason_contracts="${reason_contracts:-matched scripts: ${f}}"
      ;;
    docs/DELIVERY_DOC_INDEX.md)
      run_contracts="true"
      reason_contracts="${reason_contracts:-matched delivery doc index: ${f}}"
      ;;
    README.md|docs/RUNBOOK_*.md|docs/OPS_RUNBOOK_MT.md|docs/ERROR_CODES*.md)
      run_contracts="true"
      reason_contracts="${reason_contracts:-matched docs wiring: ${f}}"
      ;;
    migrations/*)
      run_plugin_tests="true"
      reason_plugin_tests="${reason_plugin_tests:-matched migration: ${f}}"
      break
      ;;
    package.json|package-lock.json|playwright/*)
      run_playwright="true"
      reason_playwright="${reason_playwright:-matched frontend/playwright: ${f}}"
      ;;
    src/*)
      # Ignore test-only changes for the heavier CI jobs.
      if [[ "${f}" == *"/tests/"* ]]; then
        continue
      fi
      base_name="$(basename "${f}")"
      if [[ "${base_name}" == test_*.py ]]; then
        continue
      fi
      run_plugin_tests="true"
      run_playwright="true"
      reason_plugin_tests="${reason_plugin_tests:-matched src: ${f}}"
      reason_playwright="${reason_playwright:-matched src: ${f}}"
      ;;
  esac
done < "${changed}"

if [[ "${FORCE_FULL}" == "true" ]]; then
  run_plugin_tests="true"
  run_playwright="true"
  run_contracts="true"
  reason_plugin_tests="forced by ci:full"
  reason_playwright="forced by ci:full"
  reason_contracts="forced by ci:full"
fi

echo "- run_plugin_tests: ${run_plugin_tests}"
echo "- run_plugin_tests_reason: ${reason_plugin_tests}"
echo "- run_playwright: ${run_playwright}"
echo "- run_playwright_reason: ${reason_playwright}"
echo "- run_contracts: ${run_contracts}"
echo "- run_contracts_reason: ${reason_contracts}"
echo ""

echo "## Regression Change Scope (local debug)"
echo ""
echo "- event: ${EVENT}"
echo "- force_regression: ${FORCE_REGRESSION}"
echo "- force_cadgf: ${FORCE_CADGF}"
echo ""

regression_workflow_changed="false"
if grep -q '^.github/workflows/regression.yml$' "${changed}"; then
  regression_workflow_changed="true"
fi

cadgf="false"
cadgf_reason=""
cadgf_regex='^(docker-compose\\.cadgf\\.yml|docs/samples/cadgf_preview_square\\.dxf|docs/CADGF_|scripts/verify_cad_preview_online\\.sh|scripts/verify_all\\.sh|src/yuantus/config/settings\\.py|src/yuantus/meta_engine/services/cadgf_converter_service\\.py|src/yuantus/meta_engine/tasks/cad_pipeline_tasks\\.py)'
if [[ "${EVENT}" != "pull_request" ]]; then
  cadgf_regex='^(\\.github/workflows/regression\\.yml|docker-compose\\.cadgf\\.yml|docs/samples/cadgf_preview_square\\.dxf|docs/CADGF_|scripts/verify_cad_preview_online\\.sh|scripts/verify_all\\.sh|src/yuantus/config/settings\\.py|src/yuantus/meta_engine/services/cadgf_converter_service\\.py|src/yuantus/meta_engine/tasks/cad_pipeline_tasks\\.py)'
fi
cadgf_match="$(grep -E "${cadgf_regex}" "${changed}" | head -n 1 || true)"
if [[ -n "${cadgf_match}" ]]; then
  cadgf="true"
  cadgf_reason="matched: ${cadgf_match}"
elif [[ "${EVENT}" == "pull_request" && "${regression_workflow_changed}" == "true" ]]; then
  cadgf_reason="regression.yml changed (PR) but excluded; use --force-cadgf"
fi

regression="false"
regression_reason=""
while IFS= read -r f; do
  [[ -z "${f}" ]] && continue
  case "${f}" in
    .github/workflows/regression.yml)
      if [[ "${EVENT}" == "pull_request" ]]; then
        continue
      fi
      regression="true"; regression_reason="matched workflow: ${f}"; break ;;
    alembic.ini|pyproject.toml|requirements.lock)
      regression="true"; regression_reason="matched core inputs: ${f}"; break ;;
    docker-compose*.yml|Dockerfile*)
      regression="true"; regression_reason="matched docker: ${f}"; break ;;
    migrations/*)
      regression="true"; regression_reason="matched migration: ${f}"; break ;;
    scripts/verify_all.sh|scripts/verify_*.sh)
      regression="true"; regression_reason="matched verify script: ${f}"; break ;;
    docs/samples/*)
      regression="true"; regression_reason="matched sample: ${f}"; break ;;
    src/*)
      if [[ "${f}" == *"/tests/"* ]]; then
        continue
      fi
      base_name="$(basename "${f}")"
      if [[ "${base_name}" == test_*.py ]]; then
        continue
      fi
      regression="true"; regression_reason="matched src: ${f}"; break ;;
  esac
done < "${changed}"

if [[ "${FORCE_CADGF}" == "true" ]]; then
  cadgf="true"
  cadgf_reason="forced"
fi
if [[ "${FORCE_REGRESSION}" == "true" ]]; then
  regression="true"
  regression_reason="forced"
fi

if [[ "${regression}" == "false" && "${EVENT}" == "pull_request" && "${regression_workflow_changed}" == "true" ]]; then
  regression_reason="regression.yml changed (PR) but excluded; use --force-regression"
fi

echo "- regression_workflow_changed: ${regression_workflow_changed}"
echo "- cadgf_changed: ${cadgf}"
echo "- cadgf_reason: ${cadgf_reason}"
echo "- regression_needed: ${regression}"
echo "- regression_reason: ${regression_reason}"
