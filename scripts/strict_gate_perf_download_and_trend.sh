#!/usr/bin/env bash
# Download recent strict-gate perf summary artifacts from GitHub Actions,
# then generate a local trend report.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/strict_gate_perf_download_and_trend.sh [options]

Options:
  --limit <n>            Number of recent completed runs to attempt (default: 10)
  --run-id <id[,id...]>  Download specific run id(s) directly (skip run list)
  --workflow <name>      Workflow name/id for gh run list (default: strict-gate)
  --branch <name>        Branch filter for gh run list (default: main)
  --conclusion <v>       Filter completed runs by conclusion: any|success|failure
                         (default: any)
  --max-run-age-days <n> Keep only runs created in the last N days (optional)
  --artifact-name <name> Artifact name used by `gh run download -n`
                         (default: strict-gate-perf-summary)
  --download-retries <n> Retry attempts per run for artifact download
                         (default: 1)
  --download-retry-delay-sec <n>
                         Delay between retry attempts in seconds (default: 1)
  --clean-download-dir   Remove download dir before fetching artifacts
  --fail-if-none-downloaded
                         Exit with non-zero when downloaded artifact count is 0
  --download-dir <path>  Local artifact download root
                         (default: tmp/strict-gate-artifacts/recent-perf)
  --trend-out <path>     Output trend markdown path
                         (default: <download-dir>/STRICT_GATE_PERF_TREND.md)
  --json-out <path>      Optional machine-readable summary output (JSON)
  --include-empty        Include NO_METRICS runs in trend output
  --repo <owner/name>    Optional GitHub repo for gh commands (-R)
  -h, --help             Show this help and exit

Examples:
  scripts/strict_gate_perf_download_and_trend.sh
  scripts/strict_gate_perf_download_and_trend.sh --run-id 22085198707
  scripts/strict_gate_perf_download_and_trend.sh --run-id 22085198707,22050422422
  scripts/strict_gate_perf_download_and_trend.sh --limit 20 --branch main
  scripts/strict_gate_perf_download_and_trend.sh --conclusion failure --limit 10
  scripts/strict_gate_perf_download_and_trend.sh --max-run-age-days 7 --limit 20
  scripts/strict_gate_perf_download_and_trend.sh --artifact-name strict-gate-perf-summary
  scripts/strict_gate_perf_download_and_trend.sh --download-retries 3 --download-retry-delay-sec 2
  scripts/strict_gate_perf_download_and_trend.sh --clean-download-dir --limit 10
  scripts/strict_gate_perf_download_and_trend.sh \
    --download-dir tmp/strict-gate-artifacts/perf \
    --trend-out tmp/strict-gate-artifacts/perf/STRICT_GATE_PERF_TREND.md \
    --json-out  tmp/strict-gate-artifacts/perf/strict_gate_perf_download.json
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LIMIT=10
RUN_IDS_RAW=""
WORKFLOW="strict-gate"
BRANCH="main"
CONCLUSION="any"
MAX_RUN_AGE_DAYS=""
ARTIFACT_NAME="strict-gate-perf-summary"
DOWNLOAD_RETRIES=1
DOWNLOAD_RETRY_DELAY_SEC=1
CLEAN_DOWNLOAD_DIR=0
FAIL_IF_NONE_DOWNLOADED=0
DOWNLOAD_DIR="${REPO_ROOT}/tmp/strict-gate-artifacts/recent-perf"
TREND_OUT=""
JSON_OUT=""
INCLUDE_EMPTY=0
REPO_ARG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)
      LIMIT="${2:-}"
      shift 2
      ;;
    --run-id)
      RUN_IDS_RAW="${RUN_IDS_RAW}${RUN_IDS_RAW:+ }${2:-}"
      shift 2
      ;;
    --workflow)
      WORKFLOW="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    --conclusion)
      CONCLUSION="${2:-}"
      shift 2
      ;;
    --max-run-age-days)
      MAX_RUN_AGE_DAYS="${2:-}"
      shift 2
      ;;
    --artifact-name)
      ARTIFACT_NAME="${2:-}"
      shift 2
      ;;
    --download-retries)
      DOWNLOAD_RETRIES="${2:-}"
      shift 2
      ;;
    --download-retry-delay-sec)
      DOWNLOAD_RETRY_DELAY_SEC="${2:-}"
      shift 2
      ;;
    --clean-download-dir)
      CLEAN_DOWNLOAD_DIR=1
      shift
      ;;
    --fail-if-none-downloaded)
      FAIL_IF_NONE_DOWNLOADED=1
      shift
      ;;
    --download-dir)
      DOWNLOAD_DIR="${2:-}"
      shift 2
      ;;
    --trend-out)
      TREND_OUT="${2:-}"
      shift 2
      ;;
    --json-out)
      JSON_OUT="${2:-}"
      shift 2
      ;;
    --include-empty)
      INCLUDE_EMPTY=1
      shift
      ;;
    --repo)
      REPO_ARG="${2:-}"
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

if ! [[ "$LIMIT" =~ ^[0-9]+$ ]] || [[ "$LIMIT" -lt 1 ]]; then
  echo "ERROR: --limit must be a positive integer (got: $LIMIT)" >&2
  exit 2
fi
if [[ "$CONCLUSION" != "any" && "$CONCLUSION" != "success" && "$CONCLUSION" != "failure" ]]; then
  echo "ERROR: --conclusion must be one of: any|success|failure (got: $CONCLUSION)" >&2
  exit 2
fi
if [[ -n "$MAX_RUN_AGE_DAYS" ]] && { ! [[ "$MAX_RUN_AGE_DAYS" =~ ^[0-9]+$ ]] || [[ "$MAX_RUN_AGE_DAYS" -lt 0 ]]; }; then
  echo "ERROR: --max-run-age-days must be a non-negative integer (got: $MAX_RUN_AGE_DAYS)" >&2
  exit 2
fi
if [[ -z "$ARTIFACT_NAME" ]]; then
  echo "ERROR: --artifact-name must not be empty." >&2
  exit 2
fi
if ! [[ "$DOWNLOAD_RETRIES" =~ ^[0-9]+$ ]] || [[ "$DOWNLOAD_RETRIES" -lt 1 ]]; then
  echo "ERROR: --download-retries must be a positive integer (got: $DOWNLOAD_RETRIES)" >&2
  exit 2
fi
if ! [[ "$DOWNLOAD_RETRY_DELAY_SEC" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --download-retry-delay-sec must be a non-negative integer (got: $DOWNLOAD_RETRY_DELAY_SEC)" >&2
  exit 2
fi

if [[ -z "$TREND_OUT" ]]; then
  TREND_OUT="${DOWNLOAD_DIR}/STRICT_GATE_PERF_TREND.md"
fi

RUN_IDS=()
if [[ -n "$RUN_IDS_RAW" ]]; then
  for token in ${RUN_IDS_RAW//,/ }; do
    [[ -z "$token" ]] && continue
    if ! [[ "$token" =~ ^[0-9]+$ ]]; then
      echo "ERROR: --run-id only accepts numeric run ids (bad token: $token)" >&2
      exit 2
    fi
    RUN_IDS+=("$token")
  done
  if [[ "${#RUN_IDS[@]}" -eq 0 ]]; then
    echo "ERROR: --run-id was provided but no valid run ids were parsed." >&2
    exit 2
  fi
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

trend_script="${REPO_ROOT}/scripts/strict_gate_perf_trend.py"
if [[ ! -f "$trend_script" ]]; then
  echo "ERROR: missing trend script: $trend_script" >&2
  exit 2
fi

if [[ "$CLEAN_DOWNLOAD_DIR" -eq 1 ]]; then
  download_dir_abs="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$DOWNLOAD_DIR")"
  repo_root_abs="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$REPO_ROOT")"
  if [[ "$download_dir_abs" == "/" || "$download_dir_abs" == "$repo_root_abs" ]]; then
    echo "ERROR: refusing to clean unsafe --download-dir: ${download_dir_abs}" >&2
    exit 2
  fi
  if [[ -d "$DOWNLOAD_DIR" ]]; then
    echo "==> Clean download dir: ${DOWNLOAD_DIR}"
    rm -rf "$DOWNLOAD_DIR"
  fi
fi
mkdir -p "$DOWNLOAD_DIR"

LIST_LIMIT=$((LIMIT * 3))
if [[ "$LIST_LIMIT" -lt 30 ]]; then
  LIST_LIMIT=30
fi

gh_args=(run list --workflow "$WORKFLOW" --branch "$BRANCH" --limit "$LIST_LIMIT" --json databaseId,status,conclusion,createdAt)
if [[ -n "$REPO_ARG" ]]; then
  gh_args+=(-R "$REPO_ARG")
fi

run_ids=""
if [[ "${#RUN_IDS[@]}" -gt 0 ]]; then
  if [[ "$CONCLUSION" != "any" ]]; then
    echo "INFO: --conclusion is ignored when --run-id is explicitly provided." >&2
  fi
  if [[ -n "$MAX_RUN_AGE_DAYS" ]]; then
    echo "INFO: --max-run-age-days is ignored when --run-id is explicitly provided." >&2
  fi
  echo "==> Use explicit run ids: ${RUN_IDS[*]}"
  run_ids="$(printf '%s\n' "${RUN_IDS[@]}")"
else
  echo "==> Discover recent runs (workflow=${WORKFLOW}, branch=${BRANCH}, conclusion=${CONCLUSION}, max_run_age_days=${MAX_RUN_AGE_DAYS:-any}, limit=${LIMIT})"
  run_ids="$(
    gh "${gh_args[@]}" | python3 -c '
import json
import sys
from datetime import datetime, timezone

target = int(sys.argv[1])
conclusion_filter = sys.argv[2]
max_age_raw = sys.argv[3]
max_age_days = int(max_age_raw) if max_age_raw.strip() else None
raw = sys.stdin.read()
if not raw.strip():
    print("", end="")
    raise SystemExit(0)
rows = json.loads(raw)
picked = []
for row in rows:
    if row.get("status") != "completed":
        continue
    if conclusion_filter != "any" and row.get("conclusion") != conclusion_filter:
        continue
    if max_age_days is not None:
        created_at = row.get("createdAt")
        if created_at:
            try:
                dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
                if age_days > max_age_days:
                    continue
            except Exception:
                pass
    run_id = row.get("databaseId")
    if not run_id:
        continue
    picked.append(str(run_id))
    if len(picked) >= target:
        break
print("\n".join(picked))
' "$LIMIT" "$CONCLUSION" "$MAX_RUN_AGE_DAYS"
  )"
fi

if [[ -z "$run_ids" ]]; then
  echo "WARN: no matching runs found for workflow=${WORKFLOW} branch=${BRANCH} conclusion=${CONCLUSION} max_run_age_days=${MAX_RUN_AGE_DAYS:-any}" >&2
fi

downloaded=0
skipped=0
selected_run_ids=()
downloaded_run_ids=()
skipped_run_ids=()
run_results=()

while IFS= read -r run_id; do
  [[ -z "$run_id" ]] && continue
  selected_run_ids+=("$run_id")
  echo "==> Download artifact ${ARTIFACT_NAME} (run_id=${run_id})"
  dl_args=(run download "$run_id" -n "$ARTIFACT_NAME" -D "$DOWNLOAD_DIR")
  if [[ -n "$REPO_ARG" ]]; then
    dl_args+=(-R "$REPO_ARG")
  fi
  attempt=1
  attempt_used=0
  dl_ok=0
  while [[ "$attempt" -le "$DOWNLOAD_RETRIES" ]]; do
    attempt_used="$attempt"
    if gh "${dl_args[@]}" >/dev/null 2>&1; then
      dl_ok=1
      break
    fi
    if [[ "$attempt" -lt "$DOWNLOAD_RETRIES" ]]; then
      echo "WARN: download attempt ${attempt}/${DOWNLOAD_RETRIES} failed for run_id=${run_id}; retry in ${DOWNLOAD_RETRY_DELAY_SEC}s." >&2
      if [[ "$DOWNLOAD_RETRY_DELAY_SEC" -gt 0 ]]; then
        sleep "$DOWNLOAD_RETRY_DELAY_SEC"
      fi
    fi
    attempt=$((attempt + 1))
  done
  if [[ "$dl_ok" -eq 1 ]]; then
    downloaded=$((downloaded + 1))
    downloaded_run_ids+=("$run_id")
  else
    echo "WARN: unable to download ${ARTIFACT_NAME} for run_id=${run_id}" >&2
    skipped=$((skipped + 1))
    skipped_run_ids+=("$run_id")
  fi
  run_results+=("${run_id}:${dl_ok}:${attempt_used}")
done <<< "$run_ids"

summary_dir="${DOWNLOAD_DIR}/docs/DAILY_REPORTS"
mkdir -p "$summary_dir"
mkdir -p "$(dirname "$TREND_OUT")"
if [[ -n "$JSON_OUT" ]]; then
  mkdir -p "$(dirname "$JSON_OUT")"
fi

trend_args=(
  "$trend_script"
  --dir "$summary_dir"
  --glob 'STRICT_GATE_*_PERF.md'
  --out "$TREND_OUT"
  --limit "$LIMIT"
)
if [[ "$INCLUDE_EMPTY" -eq 1 ]]; then
  trend_args+=(--include-empty)
fi

echo "==> Generate trend report"
python3 "${trend_args[@]}"

if [[ -n "$JSON_OUT" ]]; then
  python3 - "$JSON_OUT" \
    "$WORKFLOW" "$BRANCH" "$CONCLUSION" "$MAX_RUN_AGE_DAYS" "$ARTIFACT_NAME" \
    "$DOWNLOAD_RETRIES" "$DOWNLOAD_RETRY_DELAY_SEC" \
    "$LIMIT" "$TREND_OUT" "$summary_dir" \
    "$downloaded" "$skipped" "$INCLUDE_EMPTY" "$RUN_IDS_RAW" \
    "$FAIL_IF_NONE_DOWNLOADED" "$CLEAN_DOWNLOAD_DIR" \
    "$(printf '%s,' "${selected_run_ids[@]}")" \
    "$(printf '%s,' "${downloaded_run_ids[@]}")" \
    "$(printf '%s,' "${skipped_run_ids[@]}")" \
    "$(printf '%s,' "${run_results[@]}")" <<'PY'
import json
import sys
from datetime import datetime, timezone


def split_csv(s: str):
    return [x for x in s.split(",") if x]


def parse_run_results(s: str):
    rows = []
    for raw in split_csv(s):
        parts = raw.split(":")
        if len(parts) != 3:
            continue
        run_id, downloaded_raw, attempts_raw = parts
        try:
            attempts = int(attempts_raw)
        except ValueError:
            attempts = 0
        rows.append(
            {
                "run_id": run_id,
                "downloaded": downloaded_raw == "1",
                "attempts": attempts,
            }
        )
    return rows


out_path = sys.argv[1]
payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "workflow": sys.argv[2],
    "branch": sys.argv[3],
    "conclusion": sys.argv[4],
    "max_run_age_days": int(sys.argv[5]) if sys.argv[5].strip() else None,
    "artifact_name": sys.argv[6],
    "download_retries": int(sys.argv[7]),
    "download_retry_delay_sec": int(sys.argv[8]),
    "limit": int(sys.argv[9]),
    "trend_report": sys.argv[10],
    "summary_dir": sys.argv[11],
    "downloaded_count": int(sys.argv[12]),
    "skipped_count": int(sys.argv[13]),
    "include_empty": sys.argv[14] == "1",
    "run_id_mode": bool(sys.argv[15].strip()),
    "run_id_input_raw": sys.argv[15],
    "fail_if_none_downloaded": sys.argv[16] == "1",
    "failed_due_to_zero_downloads": (sys.argv[16] == "1") and (int(sys.argv[12]) == 0),
    "clean_download_dir": sys.argv[17] == "1",
    "selected_run_ids": split_csv(sys.argv[18]),
    "downloaded_run_ids": split_csv(sys.argv[19]),
    "skipped_run_ids": split_csv(sys.argv[20]),
    "run_results": parse_run_results(sys.argv[21]),
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
print(out_path)
PY
fi

echo ""
echo "Downloaded artifacts: ${downloaded}"
echo "Skipped downloads: ${skipped}"
echo "Summary dir: ${summary_dir}"
echo "Trend report: ${TREND_OUT}"
if [[ -n "$JSON_OUT" ]]; then
  echo "JSON summary: ${JSON_OUT}"
fi
if [[ "$FAIL_IF_NONE_DOWNLOADED" -eq 1 && "$downloaded" -eq 0 ]]; then
  echo "ERROR: no artifacts downloaded; failing due to --fail-if-none-downloaded." >&2
  exit 1
fi
