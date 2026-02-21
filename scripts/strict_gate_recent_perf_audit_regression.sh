#!/usr/bin/env bash
# Run two strict-gate workflow_dispatch checks and assert recent perf audit gating behavior.
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/strict_gate_recent_perf_audit_regression.sh [options]

Options:
  --workflow <name>                 Workflow identifier for gh commands (default: strict-gate.yml)
  --ref <branch-or-tag>             Ref used for workflow_dispatch (default: main)
  --repo <owner/name>               Optional repository override for gh (-R)
  --poll-interval-sec <n>           Poll interval for run discovery/waiting (default: 8)
  --max-wait-sec <n>                Maximum seconds to wait per run completion (default: 1800)
  --success-limit <n>               Valid case recent_perf_audit_limit value (default: 10)
  --success-max-run-age-days <n>    Valid case recent_perf_max_run_age_days value (default: 1)
  --success-conclusion <value>      Valid case recent_perf_conclusion (default: success)
  --summary-json <path>             Optional JSON summary output path
                                    (default: <out-dir>/STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json)
  --out-dir <path>                  Output directory for downloaded evidence
                                    (default: tmp/strict-gate-artifacts/recent-perf-regression/<timestamp>)
  -h, --help                        Show help

What it does:
  1) Triggers an invalid dispatch input case and asserts:
     - Validate recent perf audit inputs: failure
     - Optional recent perf audit (download + trend): skipped
     - Upload strict gate recent perf audit: skipped
  2) Triggers a valid dispatch input case and asserts:
     - Validate recent perf audit inputs: success
     - Optional recent perf audit (download + trend): success
     - Upload strict gate recent perf audit: success
  3) Downloads strict-gate-recent-perf-audit artifact from the valid run
     and verifies strict_gate_perf_download.json key fields.
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

WORKFLOW="strict-gate.yml"
REF="main"
REPO=""
POLL_INTERVAL_SEC=8
MAX_WAIT_SEC=1800
SUCCESS_LIMIT=10
SUCCESS_MAX_RUN_AGE_DAYS=1
SUCCESS_CONCLUSION="success"
OUT_DIR="${REPO_ROOT}/tmp/strict-gate-artifacts/recent-perf-regression/$(date +%Y%m%d-%H%M%S)"
SUMMARY_JSON=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workflow)
      WORKFLOW="${2:-}"
      shift 2
      ;;
    --ref)
      REF="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --poll-interval-sec)
      POLL_INTERVAL_SEC="${2:-}"
      shift 2
      ;;
    --max-wait-sec)
      MAX_WAIT_SEC="${2:-}"
      shift 2
      ;;
    --success-limit)
      SUCCESS_LIMIT="${2:-}"
      shift 2
      ;;
    --success-max-run-age-days)
      SUCCESS_MAX_RUN_AGE_DAYS="${2:-}"
      shift 2
      ;;
    --success-conclusion)
      SUCCESS_CONCLUSION="${2:-}"
      shift 2
      ;;
    --summary-json)
      SUMMARY_JSON="${2:-}"
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

if ! [[ "$POLL_INTERVAL_SEC" =~ ^[0-9]+$ ]] || [[ "$POLL_INTERVAL_SEC" -lt 1 ]]; then
  echo "ERROR: --poll-interval-sec must be a positive integer (got: $POLL_INTERVAL_SEC)" >&2
  exit 2
fi
if ! [[ "$MAX_WAIT_SEC" =~ ^[0-9]+$ ]] || [[ "$MAX_WAIT_SEC" -lt 1 ]]; then
  echo "ERROR: --max-wait-sec must be a positive integer (got: $MAX_WAIT_SEC)" >&2
  exit 2
fi
if ! [[ "$SUCCESS_LIMIT" =~ ^[0-9]+$ ]] || [[ "$SUCCESS_LIMIT" -lt 1 ]]; then
  echo "ERROR: --success-limit must be a positive integer (got: $SUCCESS_LIMIT)" >&2
  exit 2
fi
if ! [[ "$SUCCESS_MAX_RUN_AGE_DAYS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --success-max-run-age-days must be a non-negative integer (got: $SUCCESS_MAX_RUN_AGE_DAYS)" >&2
  exit 2
fi
if [[ "$SUCCESS_CONCLUSION" != "any" && "$SUCCESS_CONCLUSION" != "success" && "$SUCCESS_CONCLUSION" != "failure" ]]; then
  echo "ERROR: --success-conclusion must be one of any|success|failure (got: $SUCCESS_CONCLUSION)" >&2
  exit 2
fi
if [[ -z "$OUT_DIR" ]]; then
  echo "ERROR: --out-dir must not be empty." >&2
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
if [[ -n "$REPO" ]]; then
  GH_BASE+=("-R" "$REPO")
fi
REPO_NAME_WITH_OWNER="$REPO"
if [[ -z "$REPO_NAME_WITH_OWNER" ]]; then
  REPO_NAME_WITH_OWNER="$("${GH_BASE[@]}" repo view --json nameWithOwner --jq .nameWithOwner)"
fi

HEAD_SHA="$(git -C "$REPO_ROOT" rev-parse "$REF" 2>/dev/null || true)"
if [[ -z "$HEAD_SHA" ]]; then
  echo "ERROR: failed to resolve git sha for ref: $REF" >&2
  exit 2
fi
if [[ -z "$SUMMARY_JSON" ]]; then
  SUMMARY_JSON="${OUT_DIR}/STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json"
fi

log() {
  printf '[strict-gate-recent-perf-regression] %s\n' "$*"
}

assert_equals() {
  local actual="$1"
  local expected="$2"
  local label="$3"
  if [[ "$actual" != "$expected" ]]; then
    echo "ERROR: ${label} expected '${expected}' but got '${actual}'" >&2
    exit 1
  fi
}

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local label="$3"
  if ! grep -qx "$needle" <<<"$haystack"; then
    echo "ERROR: ${label} missing expected entry: ${needle}" >&2
    exit 1
  fi
}

capture_known_ids() {
  "${GH_BASE[@]}" run list \
    --workflow "$WORKFLOW" \
    --event workflow_dispatch \
    --branch "$REF" \
    --limit 100 \
    --json databaseId,headSha \
    --jq ".[] | select(.headSha==\"${HEAD_SHA}\") | .databaseId"
}

find_new_run_id() {
  local known_ids_text="$1"
  local run_id=""

  for _ in {1..60}; do
    while IFS= read -r run_id; do
      [[ -z "$run_id" ]] && continue
      if ! grep -qx "$run_id" <<<"$known_ids_text"; then
        echo "$run_id"
        return 0
      fi
    done < <(
      "${GH_BASE[@]}" run list \
        --workflow "$WORKFLOW" \
        --event workflow_dispatch \
        --branch "$REF" \
        --limit 100 \
        --json databaseId,headSha \
        --jq ".[] | select(.headSha==\"${HEAD_SHA}\") | .databaseId"
    )
    sleep "$POLL_INTERVAL_SEC"
  done

  return 1
}

wait_for_completion() {
  local run_id="$1"
  local elapsed=0
  local run_status=""

  while true; do
    run_status="$("${GH_BASE[@]}" run view "$run_id" --json status --jq .status)"
    if [[ "$run_status" == "completed" ]]; then
      break
    fi
    if [[ "$elapsed" -ge "$MAX_WAIT_SEC" ]]; then
      echo "ERROR: timeout waiting run completion: $run_id" >&2
      exit 1
    fi
    sleep "$POLL_INTERVAL_SEC"
    elapsed=$((elapsed + POLL_INTERVAL_SEC))
  done
}

get_run_conclusion() {
  local run_id="$1"
  "${GH_BASE[@]}" run view "$run_id" --json conclusion --jq .conclusion
}

get_run_url() {
  local run_id="$1"
  "${GH_BASE[@]}" run view "$run_id" --json url --jq .url
}

get_step_conclusion() {
  local run_id="$1"
  local step_name="$2"
  local run_json

  run_json="$("${GH_BASE[@]}" run view "$run_id" --json jobs)"
  RUN_JSON="$run_json" STEP_NAME="$step_name" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["RUN_JSON"])
step_name = os.environ["STEP_NAME"]
for job in payload.get("jobs", []):
    for step in job.get("steps", []):
        if step.get("name") == step_name:
            print(step.get("conclusion") or "")
            raise SystemExit(0)
print("")
PY
}

trigger_dispatch_and_resolve_run() {
  local known_ids_text="$1"
  shift

  "${GH_BASE[@]}" workflow run "$WORKFLOW" --ref "$REF" "$@"

  local run_id
  run_id="$(find_new_run_id "$known_ids_text")" || {
    echo "ERROR: failed to discover newly triggered workflow_dispatch run." >&2
    exit 1
  }
  echo "$run_id"
}

get_artifact_names() {
  local run_id="$1"
  gh api "repos/${REPO_NAME_WITH_OWNER}/actions/runs/${run_id}/artifacts" \
    --jq '.artifacts[]?.name'
}

mkdir -p "$OUT_DIR"
log "repo_root=${REPO_ROOT}"
log "workflow=${WORKFLOW} ref=${REF} head_sha=${HEAD_SHA}"
log "out_dir=${OUT_DIR}"

log "case=invalid_inputs trigger dispatch"
invalid_known_ids="$(capture_known_ids || true)"
invalid_run_id="$(trigger_dispatch_and_resolve_run "$invalid_known_ids" \
  -f run_recent_perf_audit=true \
  -f recent_perf_audit_limit=101 \
  -f recent_perf_max_run_age_days=1 \
  -f recent_perf_conclusion=any \
  -f recent_perf_fail_if_no_metrics=true)"
log "case=invalid_inputs run_id=${invalid_run_id}"

wait_for_completion "$invalid_run_id"
invalid_conclusion="$(get_run_conclusion "$invalid_run_id")"
assert_equals "$invalid_conclusion" "failure" "invalid case run conclusion"

invalid_validate="$(get_step_conclusion "$invalid_run_id" "Validate recent perf audit inputs")"
invalid_optional="$(get_step_conclusion "$invalid_run_id" "Optional recent perf audit (download + trend)")"
invalid_upload="$(get_step_conclusion "$invalid_run_id" "Upload strict gate recent perf audit")"
assert_equals "$invalid_validate" "failure" "invalid case validate step"
assert_equals "$invalid_optional" "skipped" "invalid case optional audit step"
assert_equals "$invalid_upload" "skipped" "invalid case recent audit upload step"

if ! "${GH_BASE[@]}" run view "$invalid_run_id" --log-failed | rg -q "ERROR: recent_perf_audit_limit must be <= 100"; then
  echo "ERROR: invalid case missing expected limit validation error in failed logs" >&2
  exit 1
fi

invalid_url="$(get_run_url "$invalid_run_id")"
invalid_artifact_names="$(get_artifact_names "$invalid_run_id" || true)"
invalid_artifact_count="$(printf '%s\n' "$invalid_artifact_names" | sed '/^$/d' | wc -l | tr -d ' ')"
assert_equals "$invalid_artifact_count" "0" "invalid case artifact count"

log "case=valid_inputs trigger dispatch"
valid_known_ids="$(capture_known_ids || true)"
valid_run_id="$(trigger_dispatch_and_resolve_run "$valid_known_ids" \
  -f run_recent_perf_audit=true \
  -f recent_perf_audit_limit="${SUCCESS_LIMIT}" \
  -f recent_perf_max_run_age_days="${SUCCESS_MAX_RUN_AGE_DAYS}" \
  -f recent_perf_conclusion="${SUCCESS_CONCLUSION}" \
  -f recent_perf_fail_if_no_metrics=true)"
log "case=valid_inputs run_id=${valid_run_id}"

wait_for_completion "$valid_run_id"
valid_conclusion="$(get_run_conclusion "$valid_run_id")"
assert_equals "$valid_conclusion" "success" "valid case run conclusion"

valid_validate="$(get_step_conclusion "$valid_run_id" "Validate recent perf audit inputs")"
valid_optional="$(get_step_conclusion "$valid_run_id" "Optional recent perf audit (download + trend)")"
valid_upload="$(get_step_conclusion "$valid_run_id" "Upload strict gate recent perf audit")"
assert_equals "$valid_validate" "success" "valid case validate step"
assert_equals "$valid_optional" "success" "valid case optional audit step"
assert_equals "$valid_upload" "success" "valid case recent audit upload step"

valid_url="$(get_run_url "$valid_run_id")"
valid_artifact_names="$(get_artifact_names "$valid_run_id" || true)"
for expected_artifact in \
  "strict-gate-report" \
  "strict-gate-perf-summary" \
  "strict-gate-perf-trend" \
  "strict-gate-logs" \
  "strict-gate-recent-perf-audit"
do
  assert_contains "$valid_artifact_names" "$expected_artifact" "valid case artifact list"
done

valid_artifact_dir="${OUT_DIR}/run-${valid_run_id}-recent-perf-audit"
mkdir -p "$valid_artifact_dir"
"${GH_BASE[@]}" run download "$valid_run_id" -n strict-gate-recent-perf-audit -D "$valid_artifact_dir" >/dev/null

json_file="$(find "$valid_artifact_dir" -type f -name strict_gate_perf_download.json | head -n 1)"
if [[ -z "$json_file" ]]; then
  echo "ERROR: strict_gate_perf_download.json not found under ${valid_artifact_dir}" >&2
  exit 1
fi

python3 - "$json_file" "$SUCCESS_CONCLUSION" "$SUCCESS_MAX_RUN_AGE_DAYS" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

json_path = Path(sys.argv[1])
expected_conclusion = sys.argv[2]
expected_max_age = int(sys.argv[3])

payload = json.loads(json_path.read_text(encoding="utf-8"))
if payload.get("conclusion") != expected_conclusion:
    raise SystemExit(
        f"ERROR: json conclusion expected {expected_conclusion!r}, got {payload.get('conclusion')!r}"
    )
if payload.get("max_run_age_days") != expected_max_age:
    raise SystemExit(
        f"ERROR: json max_run_age_days expected {expected_max_age}, got {payload.get('max_run_age_days')}"
    )
if payload.get("fail_if_no_metrics") is not True:
    raise SystemExit("ERROR: json fail_if_no_metrics expected true")
if int(payload.get("downloaded_count", 0)) <= 0:
    raise SystemExit("ERROR: json downloaded_count expected > 0")
print("json_assertions=ok")
PY

summary_md="${OUT_DIR}/STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md"
cat > "$summary_md" <<SUMMARY
# Strict Gate Recent Perf Audit Regression

- workflow: ${WORKFLOW}
- ref: ${REF}
- head_sha: ${HEAD_SHA}

## Invalid Input Case (expected failure)

- run_id: ${invalid_run_id}
- url: ${invalid_url}
- run conclusion: ${invalid_conclusion}
- Validate recent perf audit inputs: ${invalid_validate}
- Optional recent perf audit (download + trend): ${invalid_optional}
- Upload strict gate recent perf audit: ${invalid_upload}
- artifact_count: ${invalid_artifact_count}

## Valid Input Case (expected success)

- run_id: ${valid_run_id}
- url: ${valid_url}
- run conclusion: ${valid_conclusion}
- Validate recent perf audit inputs: ${valid_validate}
- Optional recent perf audit (download + trend): ${valid_optional}
- Upload strict gate recent perf audit: ${valid_upload}
- artifacts:
$(printf '%s\n' "$valid_artifact_names" | sed '/^$/d' | sed 's/^/- /')
- recent audit json: ${json_file}
SUMMARY

mkdir -p "$(dirname "$SUMMARY_JSON")"
python3 - "$SUMMARY_JSON" <<PY
from __future__ import annotations

import json
from pathlib import Path

payload = {
    "workflow": "${WORKFLOW}",
    "ref": "${REF}",
    "head_sha": "${HEAD_SHA}",
    "repo": "${REPO_NAME_WITH_OWNER}",
    "invalid_case": {
        "run_id": "${invalid_run_id}",
        "url": "${invalid_url}",
        "conclusion": "${invalid_conclusion}",
        "validate_recent_perf_audit_inputs": "${invalid_validate}",
        "optional_recent_perf_audit": "${invalid_optional}",
        "upload_recent_perf_audit": "${invalid_upload}",
        "artifact_count": int("${invalid_artifact_count}"),
    },
    "valid_case": {
        "run_id": "${valid_run_id}",
        "url": "${valid_url}",
        "conclusion": "${valid_conclusion}",
        "validate_recent_perf_audit_inputs": "${valid_validate}",
        "optional_recent_perf_audit": "${valid_optional}",
        "upload_recent_perf_audit": "${valid_upload}",
        "artifacts": [line for line in """${valid_artifact_names}""".splitlines() if line.strip()],
        "recent_audit_json_path": "${json_file}",
    },
    "summary_markdown": "${summary_md}",
}

out = Path("${SUMMARY_JSON}")
out.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\\n", encoding="utf-8")
print(f"summary_json={out}")
PY

log "summary_md=${summary_md}"
log "summary_json=${SUMMARY_JSON}"
log "done"
