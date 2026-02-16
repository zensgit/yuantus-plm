#!/usr/bin/env bash
# Strict gate report generator.
#
# Runs the strict gate steps and writes a single markdown report that can be
# committed as evidence ("regression evidence autopack").
#
# Usage:
#   scripts/strict_gate_report.sh
#   OUT_DIR=tmp/strict-gate scripts/strict_gate_report.sh
#   REPORT_PATH=docs/DAILY_REPORTS/STRICT_GATE_20260207.md scripts/strict_gate_report.sh
set -uo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/strict_gate_report.sh [--help]

Environment:
  RUN_ID=<id>                Stable run id used in output folder naming.
                             Default: STRICT_GATE_<timestamp>
  OUT_DIR=<path>             Directory for logs.
                             Default: tmp/strict-gate/<run_id>
  REPORT_PATH=<path>         Markdown report output path.
                             Default: docs/DAILY_REPORTS/STRICT_GATE_<timestamp>.md

  RUN_RUN_H_E2E=1            Optional. If set, runs `scripts/verify_run_h_e2e.sh`
                             as an evidence-grade, API-only shell E2E step.
  RUN_IDENTITY_ONLY_MIGRATIONS_E2E=1
                             Optional. If set, runs `scripts/verify_identity_only_migrations.sh`
                             to verify identity-only migrations contract.
  RUN_RELEASE_ORCH_PERF=1    Optional. If set, runs
                             `scripts/verify_release_orchestration_perf_smoke.sh`.
  RUN_ESIGN_PERF=1           Optional. If set, runs
                             `scripts/verify_esign_perf_smoke.sh`.
  RUN_REPORTS_PERF=1         Optional. If set, runs
                             `scripts/verify_reports_perf_smoke.sh`.

  TARGETED_PYTEST_ARGS=<arg> Optional. If set, runs an extra targeted pytest step.
  PYTEST_BIN=<path>          Optional. Default: .venv/bin/pytest
  PLAYWRIGHT_CMD=<cmd>       Optional. Default: npx playwright test
  DEMO_SCRIPT=1              Optional. If set, runs scripts/demo_plm_closed_loop.sh

Examples:
  scripts/strict_gate_report.sh
  OUT_DIR=tmp/strict-gate/local REPORT_PATH=docs/DAILY_REPORTS/STRICT_GATE_local.md \
    scripts/strict_gate_report.sh
  TARGETED_PYTEST_ARGS='src/yuantus/meta_engine/tests/test_perf_gate_config_file.py' \
    scripts/strict_gate_report.sh
  DEMO_SCRIPT=1 scripts/strict_gate_report.sh
  RUN_RELEASE_ORCH_PERF=1 RUN_ESIGN_PERF=1 RUN_REPORTS_PERF=1 \
    scripts/strict_gate_report.sh
EOF
}

if [[ $# -ge 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
  usage
  exit 0
fi
if [[ $# -ne 0 ]]; then
  echo "ERROR: unexpected arguments: $*" >&2
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="${PYTHONPATH:-src}"

timestamp="$(date +%Y%m%d-%H%M%S)"
run_id="${RUN_ID:-STRICT_GATE_${timestamp}}"

out_dir_default="${REPO_ROOT}/tmp/strict-gate/${run_id}"
OUT_DIR="${OUT_DIR:-$out_dir_default}"

report_default="${REPO_ROOT}/docs/DAILY_REPORTS/STRICT_GATE_${timestamp}.md"
REPORT_PATH="${REPORT_PATH:-$report_default}"

mkdir -p "$OUT_DIR"
mkdir -p "$(dirname "$REPORT_PATH")"

# Render evidence paths relative to repo root so CI artifacts are easier to use.
relpath() {
  local p="$1"
  if [[ -n "${p}" && "${p}" == "${REPO_ROOT}/"* ]]; then
    echo "${p#${REPO_ROOT}/}"
  else
    echo "${p}"
  fi
}

PYTEST_BIN="${PYTEST_BIN:-${REPO_ROOT}/.venv/bin/pytest}"
PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD:-npx playwright test}"

if [[ ! -x "$PYTEST_BIN" ]]; then
  echo "ERROR: pytest not found at $PYTEST_BIN" >&2
  exit 2
fi

git_branch="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo "")"
git_sha="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo "")"
start_iso="$(date -Iseconds)"
start_epoch="$(date +%s)"

status_targeted="SKIP"
status_non_db="SKIP"
status_db="SKIP"
status_run_h_e2e="SKIP"
status_identity_only_migrations="SKIP"
status_release_orch_perf="SKIP"
status_esign_perf="SKIP"
status_reports_perf="SKIP"
status_playwright="SKIP"
status_demo="SKIP"

dur_targeted_s=0
dur_non_db_s=0
dur_db_s=0
dur_run_h_e2e_s=0
dur_identity_only_migrations_s=0
dur_release_orch_perf_s=0
dur_esign_perf_s=0
dur_reports_perf_s=0
dur_playwright_s=0
dur_demo_s=0

log_targeted="${OUT_DIR}/pytest_targeted.log"
log_non_db="${OUT_DIR}/pytest_non_db.log"
log_db="${OUT_DIR}/pytest_db.log"
log_run_h_e2e="${OUT_DIR}/verify_run_h_e2e.log"
log_identity_only_migrations="${OUT_DIR}/verify_identity_only_migrations.log"
log_release_orch_perf="${OUT_DIR}/verify_release_orchestration_perf_smoke.log"
log_esign_perf="${OUT_DIR}/verify_esign_perf_smoke.log"
log_reports_perf="${OUT_DIR}/verify_reports_perf_smoke.log"
log_playwright="${OUT_DIR}/playwright.log"
log_demo="${OUT_DIR}/demo_plm_closed_loop.log"
demo_report_path=""

run_logged() {
  local name="$1"
  local log_path="$2"
  shift 2
  echo "==> ${name}"
  # shellcheck disable=SC2068
  ( "$@" ) >"$log_path" 2>&1
  return $?
}

step() {
  local name="$1"
  local log_path="$2"
  local status_var="$3"
  local dur_var="$4"
  shift 4

  local s e ec
  s="$(date +%s)"
  if run_logged "$name" "$log_path" "$@"; then
    ec=0
    printf -v "$status_var" "PASS"
  else
    ec=$?
    printf -v "$status_var" "FAIL(%s)" "$ec"
  fi
  e="$(date +%s)"
  printf -v "$dur_var" "%s" "$((e - s))"
}

if [[ -n "${TARGETED_PYTEST_ARGS:-}" ]]; then
  step "pytest (targeted)" "$log_targeted" status_targeted dur_targeted_s \
    "$PYTEST_BIN" -q ${TARGETED_PYTEST_ARGS}
else
  echo "==> pytest (targeted): SKIP (TARGETED_PYTEST_ARGS not set)"
fi

step "pytest (non-DB)" "$log_non_db" status_non_db dur_non_db_s \
  "$PYTEST_BIN" -q

step "pytest (DB)" "$log_db" status_db dur_db_s \
  env YUANTUS_PYTEST_DB=1 "$PYTEST_BIN" -q

if [[ "${RUN_RUN_H_E2E:-}" == "1" || "${RUN_RUN_H_E2E:-}" == "true" || "${RUN_RUN_H_E2E:-}" == "yes" ]]; then
  step "verify_run_h_e2e" "$log_run_h_e2e" status_run_h_e2e dur_run_h_e2e_s \
    env OUT_DIR="${OUT_DIR}/verify-run-h-e2e" bash "${REPO_ROOT}/scripts/verify_run_h_e2e.sh"
else
  echo "==> verify_run_h_e2e: SKIP (RUN_RUN_H_E2E not set)"
fi

if [[ "${RUN_IDENTITY_ONLY_MIGRATIONS_E2E:-}" == "1" || "${RUN_IDENTITY_ONLY_MIGRATIONS_E2E:-}" == "true" || "${RUN_IDENTITY_ONLY_MIGRATIONS_E2E:-}" == "yes" ]]; then
  step "verify_identity_only_migrations" "$log_identity_only_migrations" status_identity_only_migrations dur_identity_only_migrations_s \
    env OUT_DIR="${OUT_DIR}/verify-identity-only-migrations" bash "${REPO_ROOT}/scripts/verify_identity_only_migrations.sh"
else
  echo "==> verify_identity_only_migrations: SKIP (RUN_IDENTITY_ONLY_MIGRATIONS_E2E not set)"
fi

if [[ "${RUN_RELEASE_ORCH_PERF:-}" == "1" || "${RUN_RELEASE_ORCH_PERF:-}" == "true" || "${RUN_RELEASE_ORCH_PERF:-}" == "yes" ]]; then
  step "verify_release_orchestration_perf_smoke" "$log_release_orch_perf" status_release_orch_perf dur_release_orch_perf_s \
    env OUT_DIR="${OUT_DIR}/verify-release-orchestration-perf" bash "${REPO_ROOT}/scripts/verify_release_orchestration_perf_smoke.sh"
else
  echo "==> verify_release_orchestration_perf_smoke: SKIP (RUN_RELEASE_ORCH_PERF not set)"
fi

if [[ "${RUN_ESIGN_PERF:-}" == "1" || "${RUN_ESIGN_PERF:-}" == "true" || "${RUN_ESIGN_PERF:-}" == "yes" ]]; then
  step "verify_esign_perf_smoke" "$log_esign_perf" status_esign_perf dur_esign_perf_s \
    env OUT_DIR="${OUT_DIR}/verify-esign-perf" bash "${REPO_ROOT}/scripts/verify_esign_perf_smoke.sh"
else
  echo "==> verify_esign_perf_smoke: SKIP (RUN_ESIGN_PERF not set)"
fi

if [[ "${RUN_REPORTS_PERF:-}" == "1" || "${RUN_REPORTS_PERF:-}" == "true" || "${RUN_REPORTS_PERF:-}" == "yes" ]]; then
  step "verify_reports_perf_smoke" "$log_reports_perf" status_reports_perf dur_reports_perf_s \
    env OUT_DIR="${OUT_DIR}/verify-reports-perf" bash "${REPO_ROOT}/scripts/verify_reports_perf_smoke.sh"
else
  echo "==> verify_reports_perf_smoke: SKIP (RUN_REPORTS_PERF not set)"
fi

if [[ "${DEMO_SCRIPT:-}" == "1" || "${DEMO_SCRIPT:-}" == "true" || "${DEMO_SCRIPT:-}" == "yes" ]]; then
  step "demo_plm_closed_loop" "$log_demo" status_demo dur_demo_s \
    env DEMO_RUN_ID="$run_id" bash "${REPO_ROOT}/scripts/demo_plm_closed_loop.sh"
  if [[ "$status_demo" == "PASS" ]]; then
    demo_report_path="$(grep -E '^DEMO_REPORT_PATH=' "$log_demo" | tail -n 1 | cut -d= -f2- || true)"
  fi
else
  echo "==> demo_plm_closed_loop: SKIP (DEMO_SCRIPT not set)"
fi

step "playwright" "$log_playwright" status_playwright dur_playwright_s \
  bash -lc "$PLAYWRIGHT_CMD"

end_iso="$(date -Iseconds)"
end_epoch="$(date +%s)"
total_s="$((end_epoch - start_epoch))"

overall="PASS"
for s in "$status_targeted" "$status_non_db" "$status_db" "$status_run_h_e2e" "$status_identity_only_migrations" "$status_release_orch_perf" "$status_esign_perf" "$status_reports_perf" "$status_demo" "$status_playwright"; do
  if [[ "$s" == FAIL* ]]; then
    overall="FAIL"
    break
  fi
done

cat >"$REPORT_PATH" <<EOF
# Strict Gate Report

- Run ID: \`$run_id\`
- Started: \`$start_iso\`
- Ended: \`$end_iso\`
- Duration: \`${total_s}s\`
- Git: \`${git_branch}@${git_sha}\`

## Results

| Step | Status | Duration | Log |
| --- | --- | --- | --- |
| pytest (targeted) | $status_targeted | ${dur_targeted_s}s | \`$(relpath "$log_targeted")\` |
| pytest (non-DB) | $status_non_db | ${dur_non_db_s}s | \`$(relpath "$log_non_db")\` |
| pytest (DB) | $status_db | ${dur_db_s}s | \`$(relpath "$log_db")\` |
| verify_run_h_e2e | $status_run_h_e2e | ${dur_run_h_e2e_s}s | \`$(relpath "$log_run_h_e2e")\` |
| verify_identity_only_migrations | $status_identity_only_migrations | ${dur_identity_only_migrations_s}s | \`$(relpath "$log_identity_only_migrations")\` |
| verify_release_orchestration_perf_smoke | $status_release_orch_perf | ${dur_release_orch_perf_s}s | \`$(relpath "$log_release_orch_perf")\` |
| verify_esign_perf_smoke | $status_esign_perf | ${dur_esign_perf_s}s | \`$(relpath "$log_esign_perf")\` |
| verify_reports_perf_smoke | $status_reports_perf | ${dur_reports_perf_s}s | \`$(relpath "$log_reports_perf")\` |
| demo_plm_closed_loop | $status_demo | ${dur_demo_s}s | \`$(relpath "$log_demo")\` |
| playwright | $status_playwright | ${dur_playwright_s}s | \`$(relpath "$log_playwright")\` |

## Notes

- \`TARGETED_PYTEST_ARGS\`: \`${TARGETED_PYTEST_ARGS:-<unset>}\`
- \`PLAYWRIGHT_CMD\`: \`${PLAYWRIGHT_CMD}\`
- \`DEMO_SCRIPT\`: \`${DEMO_SCRIPT:-<unset>}\`
- \`DEMO_REPORT_PATH\`: \`${demo_report_path:-<unset>}\`
- \`RUN_RUN_H_E2E\`: \`${RUN_RUN_H_E2E:-<unset>}\`
- \`RUN_IDENTITY_ONLY_MIGRATIONS_E2E\`: \`${RUN_IDENTITY_ONLY_MIGRATIONS_E2E:-<unset>}\`
- \`RUN_RELEASE_ORCH_PERF\`: \`${RUN_RELEASE_ORCH_PERF:-<unset>}\`
- \`RUN_ESIGN_PERF\`: \`${RUN_ESIGN_PERF:-<unset>}\`
- \`RUN_REPORTS_PERF\`: \`${RUN_REPORTS_PERF:-<unset>}\`
- This report is generated by \`scripts/strict_gate_report.sh\`.
EOF

if [[ "$overall" != "PASS" ]]; then
  {
    echo ""
    echo "## Failure Tails"
    echo ""
    echo "The following sections include a short tail of logs for failing steps to speed up triage in CI."
    echo ""
  } >>"$REPORT_PATH"

  if [[ "$status_targeted" == FAIL* ]]; then
    {
      echo "### pytest (targeted)"
      echo ""
      echo '```text'
      tail -n 120 "$log_targeted" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_non_db" == FAIL* ]]; then
    {
      echo "### pytest (non-DB)"
      echo ""
      echo '```text'
      tail -n 120 "$log_non_db" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_db" == FAIL* ]]; then
    {
      echo "### pytest (DB)"
      echo ""
      echo '```text'
      tail -n 120 "$log_db" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_run_h_e2e" == FAIL* ]]; then
    {
      echo "### verify_run_h_e2e"
      echo ""
      echo '```text'
      tail -n 120 "$log_run_h_e2e" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_identity_only_migrations" == FAIL* ]]; then
    {
      echo "### verify_identity_only_migrations"
      echo ""
      echo '```text'
      tail -n 120 "$log_identity_only_migrations" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_release_orch_perf" == FAIL* ]]; then
    {
      echo "### verify_release_orchestration_perf_smoke"
      echo ""
      echo '```text'
      tail -n 160 "$log_release_orch_perf" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_esign_perf" == FAIL* ]]; then
    {
      echo "### verify_esign_perf_smoke"
      echo ""
      echo '```text'
      tail -n 160 "$log_esign_perf" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_reports_perf" == FAIL* ]]; then
    {
      echo "### verify_reports_perf_smoke"
      echo ""
      echo '```text'
      tail -n 160 "$log_reports_perf" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_demo" == FAIL* ]]; then
    {
      echo "### demo_plm_closed_loop"
      echo ""
      echo '```text'
      tail -n 160 "$log_demo" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
  if [[ "$status_playwright" == FAIL* ]]; then
    {
      echo "### playwright"
      echo ""
      echo '```text'
      tail -n 160 "$log_playwright" || true
      echo '```'
      echo ""
    } >>"$REPORT_PATH"
  fi
fi

echo ""
echo "Report: $REPORT_PATH"
echo "Logs: $OUT_DIR"
echo "STRICT_GATE_REPORT: $overall"
echo "STRICT_GATE_REPORT_PATH: $(relpath "$REPORT_PATH")"
echo "STRICT_GATE_LOG_DIR: $(relpath "$OUT_DIR")"

if [[ "$overall" != "PASS" ]]; then
  exit 1
fi
