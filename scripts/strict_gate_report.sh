#!/usr/bin/env bash
# Strict gate report generator.
#
# Runs the strict gate steps and writes a single markdown report that can be
# committed as evidence ("regression evidence autopack").
#
# Usage:
#   scripts/strict_gate_report.sh
#   OUT_DIR=tmp/strict-gate scripts/strict_gate_report.sh
#   REPORT_PATH=docs/DAILY_REPORTS/STRICT_GATE_20260207_12345.md scripts/strict_gate_report.sh
set -uo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/strict_gate_report.sh [--help]

Environment:
  RUN_ID=<id>                Stable run id used in output folder naming.
                             Default: STRICT_GATE_<timestamp>_<pid>
  OUT_DIR=<path>             Directory for logs.
                             Default: tmp/strict-gate/<run_id>
  REPORT_PATH=<path>         Markdown report output path.
                             Default: docs/DAILY_REPORTS/<run_id>.md

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
  PLAYWRIGHT_RUNNER=<path>   Optional. Default: scripts/run_playwright_strict_gate.sh
  PLAYWRIGHT_CMD=<cmd>       Optional. Default: npx playwright test --workers=1
  PLAYWRIGHT_PORT_PICKER_CMD=<cmd> Optional. Passed through to playwright runner.
  PLAYWRIGHT_MAX_ATTEMPTS=<n> Optional. Default: 2
  PLAYWRIGHT_RETRYABLE_PATTERN=<re> Optional. Passed through to playwright runner.
  PLAYWRIGHT_KEEP_DB=<bool>  Optional. 0/1, true/false, yes/no. Passed through.
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
run_id="${RUN_ID:-STRICT_GATE_${timestamp}_$$}"

out_dir_default="${REPO_ROOT}/tmp/strict-gate/${run_id}"
OUT_DIR="${OUT_DIR:-$out_dir_default}"

report_default="${REPO_ROOT}/docs/DAILY_REPORTS/${run_id}.md"
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

REQUESTED_PLAYWRIGHT_MAX_ATTEMPTS="${PLAYWRIGHT_MAX_ATTEMPTS:-<unset>}"
REQUESTED_PLAYWRIGHT_RETRYABLE_PATTERN="${PLAYWRIGHT_RETRYABLE_PATTERN:-<unset>}"
REQUESTED_PLAYWRIGHT_KEEP_DB="${PLAYWRIGHT_KEEP_DB:-<unset>}"
REQUESTED_PLAYWRIGHT_PORT="${PLAYWRIGHT_PORT:-<unset>}"
REQUESTED_PLAYWRIGHT_PORT_PICKER_CMD="${PLAYWRIGHT_PORT_PICKER_CMD:-<unset>}"
REQUESTED_PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-<unset>}"
REQUESTED_PLAYWRIGHT_DB_PATH="${PLAYWRIGHT_DB_PATH:-<unset>}"

PYTEST_BIN="${PYTEST_BIN:-${REPO_ROOT}/.venv/bin/pytest}"
PLAYWRIGHT_RUNNER="${PLAYWRIGHT_RUNNER:-${REPO_ROOT}/scripts/run_playwright_strict_gate.sh}"
PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD:-npx playwright test --workers=1}"
PLAYWRIGHT_RETRYABLE_PATTERN="${PLAYWRIGHT_RETRYABLE_PATTERN:-}"
PLAYWRIGHT_PORT="${PLAYWRIGHT_PORT:-}"
PLAYWRIGHT_PORT_PICKER_CMD="${PLAYWRIGHT_PORT_PICKER_CMD:-}"
PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-}"
PLAYWRIGHT_DB_PATH="${PLAYWRIGHT_DB_PATH:-}"
PLAYWRIGHT_MAX_ATTEMPTS="${PLAYWRIGHT_MAX_ATTEMPTS:-2}"
PLAYWRIGHT_KEEP_DB="${PLAYWRIGHT_KEEP_DB:-0}"

if ! [[ "$PLAYWRIGHT_MAX_ATTEMPTS" =~ ^[0-9]+$ ]] || [[ "$PLAYWRIGHT_MAX_ATTEMPTS" -lt 1 ]]; then
  echo "ERROR: PLAYWRIGHT_MAX_ATTEMPTS must be a positive integer, got: ${PLAYWRIGHT_MAX_ATTEMPTS}" >&2
  exit 2
fi
if [[ -n "$PLAYWRIGHT_KEEP_DB" ]]; then
  keep_db_normalized="$(printf '%s' "$PLAYWRIGHT_KEEP_DB" | tr '[:upper:]' '[:lower:]')"
  case "$keep_db_normalized" in
    0|1|true|false|yes|no|on|off) ;;
    *)
      echo "ERROR: PLAYWRIGHT_KEEP_DB must be one of 0/1/true/false/yes/no/on/off, got: ${PLAYWRIGHT_KEEP_DB}" >&2
      exit 2
      ;;
  esac
fi
if [[ -n "$PLAYWRIGHT_RETRYABLE_PATTERN" ]]; then
  grep -Eq "$PLAYWRIGHT_RETRYABLE_PATTERN" <<<"" >/dev/null 2>&1
  grep_rc=$?
  if [[ "$grep_rc" -eq 2 ]]; then
    echo "ERROR: PLAYWRIGHT_RETRYABLE_PATTERN is not a valid extended regex: ${PLAYWRIGHT_RETRYABLE_PATTERN}" >&2
    exit 2
  fi
fi

if [[ ! -x "$PYTEST_BIN" ]]; then
  echo "ERROR: pytest not found at $PYTEST_BIN" >&2
  exit 2
fi
if [[ ! -x "$PLAYWRIGHT_RUNNER" ]]; then
  echo "ERROR: playwright runner not found or not executable at $PLAYWRIGHT_RUNNER" >&2
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

run_playwright_step() {
  env \
    PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD" \
    PLAYWRIGHT_RETRYABLE_PATTERN="$PLAYWRIGHT_RETRYABLE_PATTERN" \
    PLAYWRIGHT_PORT="$PLAYWRIGHT_PORT" \
    PLAYWRIGHT_PORT_PICKER_CMD="$PLAYWRIGHT_PORT_PICKER_CMD" \
    PLAYWRIGHT_BASE_URL="$PLAYWRIGHT_BASE_URL" \
    YUANTUS_PLAYWRIGHT_DB_PATH="$PLAYWRIGHT_DB_PATH" \
    PLAYWRIGHT_MAX_ATTEMPTS="$PLAYWRIGHT_MAX_ATTEMPTS" \
    PLAYWRIGHT_KEEP_DB="$PLAYWRIGHT_KEEP_DB" \
    "$PLAYWRIGHT_RUNNER"
}

if [[ -n "${TARGETED_PYTEST_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  targeted_args=( ${TARGETED_PYTEST_ARGS} )
  step "pytest (targeted)" "$log_targeted" status_targeted dur_targeted_s \
    "$PYTEST_BIN" -q "${targeted_args[@]}"
else
  echo "==> pytest (targeted): SKIP (TARGETED_PYTEST_ARGS not set)"
fi

step "pytest (non-DB)" "$log_non_db" status_non_db dur_non_db_s \
  "$PYTEST_BIN" -q

step "pytest (DB)" "$log_db" status_db dur_db_s \
  env YUANTUS_PYTEST_DB=1 "$PYTEST_BIN" -q

if [[ "${RUN_RUN_H_E2E:-}" == "1" || "${RUN_RUN_H_E2E:-}" == "true" || "${RUN_RUN_H_E2E:-}" == "yes" ]]; then
  step "verify_run_h_e2e" "$log_run_h_e2e" status_run_h_e2e dur_run_h_e2e_s \
    env -u BASE_URL -u PORT OUT_DIR="${OUT_DIR}/verify-run-h-e2e" bash "${REPO_ROOT}/scripts/verify_run_h_e2e.sh"
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
    env -u BASE_URL -u PORT OUT_DIR="${OUT_DIR}/verify-release-orchestration-perf" bash "${REPO_ROOT}/scripts/verify_release_orchestration_perf_smoke.sh"
else
  echo "==> verify_release_orchestration_perf_smoke: SKIP (RUN_RELEASE_ORCH_PERF not set)"
fi

if [[ "${RUN_ESIGN_PERF:-}" == "1" || "${RUN_ESIGN_PERF:-}" == "true" || "${RUN_ESIGN_PERF:-}" == "yes" ]]; then
  step "verify_esign_perf_smoke" "$log_esign_perf" status_esign_perf dur_esign_perf_s \
    env -u BASE_URL -u PORT OUT_DIR="${OUT_DIR}/verify-esign-perf" bash "${REPO_ROOT}/scripts/verify_esign_perf_smoke.sh"
else
  echo "==> verify_esign_perf_smoke: SKIP (RUN_ESIGN_PERF not set)"
fi

if [[ "${RUN_REPORTS_PERF:-}" == "1" || "${RUN_REPORTS_PERF:-}" == "true" || "${RUN_REPORTS_PERF:-}" == "yes" ]]; then
  step "verify_reports_perf_smoke" "$log_reports_perf" status_reports_perf dur_reports_perf_s \
    env -u BASE_URL -u PORT OUT_DIR="${OUT_DIR}/verify-reports-perf" bash "${REPO_ROOT}/scripts/verify_reports_perf_smoke.sh"
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
  run_playwright_step

# Capture effective playwright runtime settings from runner logs.
PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST="$(grep -E '^PLAYWRIGHT_ATTEMPT=' "$log_playwright" | tail -n 1 | cut -d= -f2- || true)"
PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT="$(grep -c -E '^PLAYWRIGHT_ATTEMPT=' "$log_playwright" || true)"
PLAYWRIGHT_EFFECTIVE_PORT="$(grep -E '^PLAYWRIGHT_PORT=' "$log_playwright" | tail -n 1 | cut -d= -f2- || true)"
PLAYWRIGHT_EFFECTIVE_BASE_URL="$(grep -E '^PLAYWRIGHT_BASE_URL=' "$log_playwright" | tail -n 1 | cut -d= -f2- || true)"
PLAYWRIGHT_EFFECTIVE_DB_PATH="$(grep -E '^PLAYWRIGHT_DB_PATH=' "$log_playwright" | tail -n 1 | cut -d= -f2- || true)"
PLAYWRIGHT_EFFECTIVE_MAX_ATTEMPTS="$(grep -E '^PLAYWRIGHT_MAX_ATTEMPTS=' "$log_playwright" | tail -n 1 | cut -d= -f2- || true)"
PLAYWRIGHT_EFFECTIVE_KEEP_DB="$(grep -E '^PLAYWRIGHT_KEEP_DB=' "$log_playwright" | tail -n 1 | cut -d= -f2- || true)"
PLAYWRIGHT_EFFECTIVE_RETRYABLE_PATTERN="$(grep -E '^PLAYWRIGHT_RETRYABLE_PATTERN=' "$log_playwright" | tail -n 1 | cut -d= -f2- || true)"
PLAYWRIGHT_RETRIED="false"
if [[ "$PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT" =~ ^[0-9]+$ ]] && [[ "$PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT" -gt 1 ]]; then
  PLAYWRIGHT_RETRIED="true"
fi

# Backfill requested settings when caller leaves them unset.
if [[ -z "${PLAYWRIGHT_PORT:-}" ]]; then
  PLAYWRIGHT_PORT="$PLAYWRIGHT_EFFECTIVE_PORT"
fi
if [[ -z "${PLAYWRIGHT_BASE_URL:-}" ]]; then
  PLAYWRIGHT_BASE_URL="$PLAYWRIGHT_EFFECTIVE_BASE_URL"
fi
if [[ -z "${PLAYWRIGHT_DB_PATH:-}" ]]; then
  PLAYWRIGHT_DB_PATH="$PLAYWRIGHT_EFFECTIVE_DB_PATH"
fi
PLAYWRIGHT_ATTEMPT_LAST="$PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST"

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
- \`PLAYWRIGHT_RUNNER\`: \`${PLAYWRIGHT_RUNNER}\`
- \`PLAYWRIGHT_CMD\`: \`${PLAYWRIGHT_CMD}\`
- \`PLAYWRIGHT_MAX_ATTEMPTS\`: \`${PLAYWRIGHT_MAX_ATTEMPTS}\`
- \`PLAYWRIGHT_RETRYABLE_PATTERN\`: \`${PLAYWRIGHT_RETRYABLE_PATTERN:-<unset>}\`
- \`PLAYWRIGHT_ATTEMPT_LAST\`: \`${PLAYWRIGHT_ATTEMPT_LAST:-<unset>}\`
- \`PLAYWRIGHT_KEEP_DB\`: \`${PLAYWRIGHT_KEEP_DB}\`
- \`PLAYWRIGHT_PORT\`: \`${PLAYWRIGHT_PORT:-<unset>}\`
- \`PLAYWRIGHT_PORT_PICKER_CMD\`: \`${PLAYWRIGHT_PORT_PICKER_CMD:-<unset>}\`
- \`PLAYWRIGHT_BASE_URL\`: \`${PLAYWRIGHT_BASE_URL:-<unset>}\`
- \`PLAYWRIGHT_DB_PATH\`: \`${PLAYWRIGHT_DB_PATH:-<unset>}\`
- \`PLAYWRIGHT_REQUESTED_MAX_ATTEMPTS\`: \`${REQUESTED_PLAYWRIGHT_MAX_ATTEMPTS}\`
- \`PLAYWRIGHT_REQUESTED_RETRYABLE_PATTERN\`: \`${REQUESTED_PLAYWRIGHT_RETRYABLE_PATTERN}\`
- \`PLAYWRIGHT_REQUESTED_KEEP_DB\`: \`${REQUESTED_PLAYWRIGHT_KEEP_DB}\`
- \`PLAYWRIGHT_REQUESTED_PORT\`: \`${REQUESTED_PLAYWRIGHT_PORT}\`
- \`PLAYWRIGHT_REQUESTED_PORT_PICKER_CMD\`: \`${REQUESTED_PLAYWRIGHT_PORT_PICKER_CMD}\`
- \`PLAYWRIGHT_REQUESTED_BASE_URL\`: \`${REQUESTED_PLAYWRIGHT_BASE_URL}\`
- \`PLAYWRIGHT_REQUESTED_DB_PATH\`: \`${REQUESTED_PLAYWRIGHT_DB_PATH}\`
- \`PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST\`: \`${PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST:-<unset>}\`
- \`PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT\`: \`${PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT:-<unset>}\`
- \`PLAYWRIGHT_RETRIED\`: \`${PLAYWRIGHT_RETRIED}\`
- \`PLAYWRIGHT_EFFECTIVE_PORT\`: \`${PLAYWRIGHT_EFFECTIVE_PORT:-<unset>}\`
- \`PLAYWRIGHT_EFFECTIVE_BASE_URL\`: \`${PLAYWRIGHT_EFFECTIVE_BASE_URL:-<unset>}\`
- \`PLAYWRIGHT_EFFECTIVE_DB_PATH\`: \`${PLAYWRIGHT_EFFECTIVE_DB_PATH:-<unset>}\`
- \`PLAYWRIGHT_EFFECTIVE_MAX_ATTEMPTS\`: \`${PLAYWRIGHT_EFFECTIVE_MAX_ATTEMPTS:-<unset>}\`
- \`PLAYWRIGHT_EFFECTIVE_KEEP_DB\`: \`${PLAYWRIGHT_EFFECTIVE_KEEP_DB:-<unset>}\`
- \`PLAYWRIGHT_EFFECTIVE_RETRYABLE_PATTERN\`: \`${PLAYWRIGHT_EFFECTIVE_RETRYABLE_PATTERN:-<unset>}\`
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
