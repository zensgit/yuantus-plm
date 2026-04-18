#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_observation_regression_workflow.sh --base-url http://<target-host> [options]

Options:
  --base-url <url>               Required. API base URL passed to workflow_dispatch.
  --repo <owner/name>            Optional repository override for gh (-R).
  --ref <branch-or-tag>          Ref used for workflow_dispatch (default: main).
  --workflow <name>              Workflow identifier (default: p2-observation-regression).
  --artifact-name <name>         Artifact name to download (default: p2-observation-regression).
  --tenant-id <id>               Tenant header value (default: tenant-1).
  --org-id <id>                  Org header value (default: org-1).
  --username <name>              Login username when workflow falls back to password auth
                                 (default: admin).
  --environment <label>          Environment label recorded in OBSERVATION_RESULT.md
                                 (default: workflow-dispatch).
  --company-id <id>              Optional company filter.
  --eco-type <value>             Optional ECO category filter.
  --eco-state <value>            Optional ECO state filter.
  --deadline-from <iso>          Optional deadline lower bound filter.
  --deadline-to <iso>            Optional deadline upper bound filter.
  --poll-interval-sec <n>        Poll interval while discovering the run id (default: 5).
  --max-discovery-sec <n>        Max seconds to wait for run discovery (default: 120).
  --out-dir <path>               Local directory for summary + downloaded artifact
                                 (default: tmp/p2-observation-workflow-dispatch/<timestamp>).
  -h, --help                     Show help.

What it does:
  1) Triggers GitHub workflow_dispatch for p2-observation-regression.
  2) Polls gh run list until the new workflow run is visible.
  3) Waits for completion via gh run watch.
  4) Downloads artifact p2-observation-regression.
  5) Writes:
     - WORKFLOW_DISPATCH_RESULT.md
     - workflow_dispatch.json
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BASE_URL="${BASE_URL:-}"
REPO="${REPO:-}"
REF="${REF:-main}"
WORKFLOW="${WORKFLOW:-p2-observation-regression}"
ARTIFACT_NAME="${ARTIFACT_NAME:-p2-observation-regression}"
TENANT_ID="${TENANT_ID:-tenant-1}"
ORG_ID="${ORG_ID:-org-1}"
USERNAME="${USERNAME:-admin}"
ENVIRONMENT_NAME="${ENVIRONMENT:-workflow-dispatch}"
COMPANY_ID="${COMPANY_ID:-}"
ECO_TYPE="${ECO_TYPE:-}"
ECO_STATE="${ECO_STATE:-}"
DEADLINE_FROM="${DEADLINE_FROM:-}"
DEADLINE_TO="${DEADLINE_TO:-}"
POLL_INTERVAL_SEC="${POLL_INTERVAL_SEC:-5}"
MAX_DISCOVERY_SEC="${MAX_DISCOVERY_SEC:-120}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/tmp/p2-observation-workflow-dispatch/$(date +%Y%m%d-%H%M%S)}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --ref)
      REF="${2:-}"
      shift 2
      ;;
    --workflow)
      WORKFLOW="${2:-}"
      shift 2
      ;;
    --artifact-name)
      ARTIFACT_NAME="${2:-}"
      shift 2
      ;;
    --tenant-id)
      TENANT_ID="${2:-}"
      shift 2
      ;;
    --org-id)
      ORG_ID="${2:-}"
      shift 2
      ;;
    --username)
      USERNAME="${2:-}"
      shift 2
      ;;
    --environment)
      ENVIRONMENT_NAME="${2:-}"
      shift 2
      ;;
    --company-id)
      COMPANY_ID="${2:-}"
      shift 2
      ;;
    --eco-type)
      ECO_TYPE="${2:-}"
      shift 2
      ;;
    --eco-state)
      ECO_STATE="${2:-}"
      shift 2
      ;;
    --deadline-from)
      DEADLINE_FROM="${2:-}"
      shift 2
      ;;
    --deadline-to)
      DEADLINE_TO="${2:-}"
      shift 2
      ;;
    --poll-interval-sec)
      POLL_INTERVAL_SEC="${2:-}"
      shift 2
      ;;
    --max-discovery-sec)
      MAX_DISCOVERY_SEC="${2:-}"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

die() {
  FAILURE_REASON="$1"
  echo "ERROR: $1" >&2
  exit 1
}

if [[ -z "${BASE_URL}" ]]; then
  echo "ERROR: --base-url or BASE_URL is required." >&2
  usage >&2
  exit 2
fi
if ! [[ "${POLL_INTERVAL_SEC}" =~ ^[0-9]+$ ]] || [[ "${POLL_INTERVAL_SEC}" -lt 1 ]]; then
  echo "ERROR: --poll-interval-sec must be a positive integer (got: ${POLL_INTERVAL_SEC})" >&2
  exit 2
fi
if ! [[ "${MAX_DISCOVERY_SEC}" =~ ^[0-9]+$ ]] || [[ "${MAX_DISCOVERY_SEC}" -lt 1 ]]; then
  echo "ERROR: --max-discovery-sec must be a positive integer (got: ${MAX_DISCOVERY_SEC})" >&2
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found in PATH." >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found in PATH." >&2
  exit 2
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh is not authenticated. Run: gh auth login" >&2
  exit 2
fi

GH_BASE=(gh)
if [[ -n "${REPO}" ]]; then
  GH_BASE+=("-R" "${REPO}")
fi

REPO_NAME_WITH_OWNER="${REPO}"
if [[ -z "${REPO_NAME_WITH_OWNER}" ]]; then
  REPO_NAME_WITH_OWNER="$("${GH_BASE[@]}" repo view --json nameWithOwner --jq .nameWithOwner)"
fi

RUN_RESULT="in_progress"
FAILURE_REASON=""
RUN_ID=""
RUN_STATUS=""
RUN_CONCLUSION=""
RUN_URL=""
WATCH_EXIT_CODE=""
ARTIFACT_DIR="${OUT_DIR}/artifact"
SUMMARY_JSON="${OUT_DIR}/workflow_dispatch.json"
SUMMARY_MD="${OUT_DIR}/WORKFLOW_DISPATCH_RESULT.md"

write_summary() {
  mkdir -p "${OUT_DIR}"
  mkdir -p "${ARTIFACT_DIR}"
  WORKFLOW="${WORKFLOW}" \
  REPO_NAME_WITH_OWNER="${REPO_NAME_WITH_OWNER}" \
  REF="${REF}" \
  BASE_URL="${BASE_URL}" \
  TENANT_ID="${TENANT_ID}" \
  ORG_ID="${ORG_ID}" \
  USERNAME="${USERNAME}" \
  ENVIRONMENT_NAME="${ENVIRONMENT_NAME}" \
  COMPANY_ID="${COMPANY_ID}" \
  ECO_TYPE="${ECO_TYPE}" \
  ECO_STATE="${ECO_STATE}" \
  DEADLINE_FROM="${DEADLINE_FROM}" \
  DEADLINE_TO="${DEADLINE_TO}" \
  ARTIFACT_NAME="${ARTIFACT_NAME}" \
  RUN_RESULT="${RUN_RESULT}" \
  FAILURE_REASON="${FAILURE_REASON}" \
  RUN_ID="${RUN_ID}" \
  RUN_STATUS="${RUN_STATUS}" \
  RUN_CONCLUSION="${RUN_CONCLUSION}" \
  RUN_URL="${RUN_URL}" \
  WATCH_EXIT_CODE="${WATCH_EXIT_CODE}" \
  ARTIFACT_DIR="${ARTIFACT_DIR}" \
  SUMMARY_MD="${SUMMARY_MD}" \
  SUMMARY_JSON="${SUMMARY_JSON}" \
  python3 - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "workflow": os.environ["WORKFLOW"],
    "repo": os.environ["REPO_NAME_WITH_OWNER"],
    "ref": os.environ["REF"],
    "base_url": os.environ["BASE_URL"],
    "tenant_id": os.environ["TENANT_ID"],
    "org_id": os.environ["ORG_ID"],
    "username": os.environ["USERNAME"],
    "environment": os.environ["ENVIRONMENT_NAME"],
    "company_id": os.environ["COMPANY_ID"],
    "eco_type": os.environ["ECO_TYPE"],
    "eco_state": os.environ["ECO_STATE"],
    "deadline_from": os.environ["DEADLINE_FROM"],
    "deadline_to": os.environ["DEADLINE_TO"],
    "artifact_name": os.environ["ARTIFACT_NAME"],
    "result": os.environ["RUN_RESULT"],
    "failure_reason": os.environ["FAILURE_REASON"],
    "run_id": os.environ["RUN_ID"],
    "run_status": os.environ["RUN_STATUS"],
    "run_conclusion": os.environ["RUN_CONCLUSION"],
    "run_url": os.environ["RUN_URL"],
    "watch_exit_code": os.environ["WATCH_EXIT_CODE"],
    "artifact_dir": os.environ["ARTIFACT_DIR"],
    "summary_md": os.environ["SUMMARY_MD"],
}
Path(os.environ["SUMMARY_JSON"]).write_text(
    json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

  cat > "${SUMMARY_MD}" <<EOF
# P2 Observation Workflow Dispatch Result

- workflow: ${WORKFLOW}
- repo: ${REPO_NAME_WITH_OWNER}
- ref: ${REF}
- result: ${RUN_RESULT}
- failure_reason: ${FAILURE_REASON:-none}
- base_url: \`${BASE_URL}\`
- run_id: ${RUN_ID:-pending}
- run_status: ${RUN_STATUS:-unknown}
- run_conclusion: ${RUN_CONCLUSION:-unknown}
- run_url: ${RUN_URL:-pending}
- artifact_name: ${ARTIFACT_NAME}
- artifact_dir: \`${ARTIFACT_DIR}\`
- summary_json: \`${SUMMARY_JSON}\`

## Inputs

- tenant_id: \`${TENANT_ID}\`
- org_id: \`${ORG_ID}\`
- username: \`${USERNAME}\`
- environment: \`${ENVIRONMENT_NAME}\`
- company_id: \`${COMPANY_ID}\`
- eco_type: \`${ECO_TYPE}\`
- eco_state: \`${ECO_STATE}\`
- deadline_from: \`${DEADLINE_FROM}\`
- deadline_to: \`${DEADLINE_TO}\`

## Next

- Open \`${ARTIFACT_DIR}\`
- Check downloaded \`OBSERVATION_RESULT.md\` / \`OBSERVATION_EVAL.md\`
EOF
}

on_exit() {
  local exit_code=$?
  trap - EXIT
  if [[ "${RUN_RESULT}" == "in_progress" ]]; then
    if [[ "${exit_code}" -eq 0 ]]; then
      RUN_RESULT="success"
    else
      RUN_RESULT="failure"
    fi
  fi
  write_summary || true
  exit "${exit_code}"
}

trap on_exit EXIT

discover_run_id() {
  local deadline=$((SECONDS + MAX_DISCOVERY_SEC))
  local run_json
  local discovered
  while (( SECONDS < deadline )); do
    run_json="$("${GH_BASE[@]}" run list --workflow "${WORKFLOW}" --branch "${REF}" --limit 20 --json databaseId,event,headBranch,createdAt 2>/dev/null || true)"
    if [[ -n "${run_json}" ]]; then
      discovered="$(
        RUN_LIST_JSON="${run_json}" \
        REF_VALUE="${REF}" \
        DISPATCH_EPOCH="${DISPATCH_EPOCH}" \
        python3 - <<'PY'
import json
import os
import sys
from datetime import datetime

raw = os.environ["RUN_LIST_JSON"]
ref = os.environ["REF_VALUE"]
dispatch_epoch = float(os.environ["DISPATCH_EPOCH"])

try:
    rows = json.loads(raw)
except Exception:
    raise SystemExit(1)

if not isinstance(rows, list):
    raise SystemExit(1)

def parse_created_at(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None

def normalize_id(value):
    if value in ("", None):
        return None
    return str(value)

fresh_candidates: list[tuple[float, str]] = []
missing_timestamp_candidates: list[str] = []

for row in rows:
    if not isinstance(row, dict):
        continue
    if row.get("event") != "workflow_dispatch":
        continue
    head_branch = row.get("headBranch")
    if isinstance(head_branch, str) and head_branch and head_branch != ref:
        continue
    run_id = normalize_id(row.get("databaseId"))
    if run_id is None:
        continue
    created_at = parse_created_at(row.get("createdAt"))
    if created_at is None:
        missing_timestamp_candidates.append(run_id)
        continue
    if created_at + 2 >= dispatch_epoch:
        fresh_candidates.append((created_at, run_id))

if fresh_candidates:
    fresh_candidates.sort(reverse=True)
    print(fresh_candidates[0][1])
    raise SystemExit(0)

if missing_timestamp_candidates:
    print(missing_timestamp_candidates[0])
    raise SystemExit(0)

raise SystemExit(1)
PY
      )" || true
      if [[ -n "${discovered}" ]]; then
        echo "${discovered}"
        return 0
      fi
    fi
    sleep "${POLL_INTERVAL_SEC}"
  done
  return 1
}

echo "== P2 observation workflow dispatch =="
echo "WORKFLOW=${WORKFLOW}"
echo "REPO=${REPO_NAME_WITH_OWNER}"
echo "REF=${REF}"
echo "BASE_URL=${BASE_URL}"
echo "OUT_DIR=${OUT_DIR}"
echo

mkdir -p "${OUT_DIR}"
mkdir -p "${ARTIFACT_DIR}"

DISPATCH_EPOCH="$(python3 - <<'PY'
import time
print(time.time())
PY
)"

echo "[1/4] Dispatch workflow"
"${GH_BASE[@]}" workflow run "${WORKFLOW}" \
  --ref "${REF}" \
  --field "base_url=${BASE_URL}" \
  --field "tenant_id=${TENANT_ID}" \
  --field "org_id=${ORG_ID}" \
  --field "username=${USERNAME}" \
  --field "environment=${ENVIRONMENT_NAME}" \
  --field "company_id=${COMPANY_ID}" \
  --field "eco_type=${ECO_TYPE}" \
  --field "eco_state=${ECO_STATE}" \
  --field "deadline_from=${DEADLINE_FROM}" \
  --field "deadline_to=${DEADLINE_TO}" \
  >/dev/null || die "failed to dispatch workflow ${WORKFLOW}"

echo "[2/4] Discover run id"
RUN_ID="$(discover_run_id)" || die "failed to discover workflow run id within ${MAX_DISCOVERY_SEC}s"
echo "run_id=${RUN_ID}"

echo "[3/4] Watch run"
WATCH_EXIT_CODE="0"
set +e
"${GH_BASE[@]}" run watch "${RUN_ID}" --exit-status
WATCH_EXIT_CODE="$?"
set -e
RUN_STATUS="$("${GH_BASE[@]}" run view "${RUN_ID}" --json status --jq .status)" || die "failed to query workflow run status"
RUN_CONCLUSION="$("${GH_BASE[@]}" run view "${RUN_ID}" --json conclusion --jq .conclusion)" || die "failed to query workflow run conclusion"
RUN_URL="$("${GH_BASE[@]}" run view "${RUN_ID}" --json url --jq .url)" || die "failed to query workflow run url"

echo "[4/4] Download artifact ${ARTIFACT_NAME}"
"${GH_BASE[@]}" run download "${RUN_ID}" -n "${ARTIFACT_NAME}" -D "${ARTIFACT_DIR}" >/dev/null || die "failed to download artifact ${ARTIFACT_NAME} for run ${RUN_ID}"

if [[ "${WATCH_EXIT_CODE}" != "0" || "${RUN_CONCLUSION}" != "success" ]]; then
  die "workflow run ${RUN_ID} completed with conclusion=${RUN_CONCLUSION:-unknown}"
fi

RUN_RESULT="success"

echo
echo "Done:"
echo "  ${SUMMARY_MD}"
echo "  ${SUMMARY_JSON}"
echo "  ${ARTIFACT_DIR}"
