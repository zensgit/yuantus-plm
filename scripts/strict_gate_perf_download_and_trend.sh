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
  --fail-if-no-runs      Exit with non-zero when no run is selected
  --fail-if-no-metrics   Exit with non-zero when selected runs have no metric tables
  --fail-if-skipped      Exit with non-zero when skipped download count > 0
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
  scripts/strict_gate_perf_download_and_trend.sh --fail-if-no-runs --limit 10
  scripts/strict_gate_perf_download_and_trend.sh --fail-if-no-metrics --limit 10
  scripts/strict_gate_perf_download_and_trend.sh --fail-if-skipped --limit 10
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
FAIL_IF_NO_RUNS=0
FAIL_IF_NO_METRICS=0
FAIL_IF_SKIPPED=0
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
    --fail-if-no-runs)
      FAIL_IF_NO_RUNS=1
      shift
      ;;
    --fail-if-no-metrics)
      FAIL_IF_NO_METRICS=1
      shift
      ;;
    --fail-if-skipped)
      FAIL_IF_SKIPPED=1
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
        if not created_at:
            continue
        try:
            dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
            if age_days > max_age_days:
                continue
        except Exception:
            continue
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

# gh run download may place report files either under docs/DAILY_REPORTS/ or
# directly under the download root depending on artifact layout. Normalize all
# discovered STRICT_GATE_*_PERF.md files into summary_dir for stable trend/count logic.
normalize_counts="$(
  python3 - "$DOWNLOAD_DIR" "$summary_dir" <<'PY'
from pathlib import Path
import shutil
import sys

download_dir = Path(sys.argv[1]).resolve()
summary_dir = Path(sys.argv[2]).resolve()
summary_dir.mkdir(parents=True, exist_ok=True)

discovered = 0
normalized = 0
for p in sorted(download_dir.rglob("STRICT_GATE_CI_*_PERF.md")):
    if not p.is_file():
        continue
    discovered += 1
    dst = summary_dir / p.name
    if p.resolve() == dst.resolve():
        continue
    shutil.copy2(p, dst)
    normalized += 1

print(f"{discovered},{normalized}")
PY
)"
IFS=',' read -r DISCOVERED_PERF_FILES NORMALIZED_PERF_FILES <<< "$normalize_counts"

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

selected_run_ids_csv="$(printf '%s,' "${selected_run_ids[@]}")"
perf_counts="$(
  python3 - "$summary_dir" "$selected_run_ids_csv" <<'PY'
from pathlib import Path
import sys

TABLE_HEADER = "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |"


def split_csv(s: str):
    return [x for x in s.split(",") if x]


def has_metric_rows(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    in_table = False
    for line in lines:
        if line.strip() == TABLE_HEADER:
            in_table = True
            continue
        if not in_table:
            continue
        if not line.strip().startswith("|"):
            break
        if line.strip().startswith("| ---"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 6 and cols[0]:
            return True
    return False


summary_dir = Path(sys.argv[1])
selected_run_ids = split_csv(sys.argv[2])

perf_report_count = 0
metric_report_count = 0
no_metric_report_count = 0

for run_id in selected_run_ids:
    p = summary_dir / f"STRICT_GATE_CI_{run_id}_PERF.md"
    if not p.is_file():
        continue
    perf_report_count += 1
    if has_metric_rows(p):
        metric_report_count += 1
    else:
        no_metric_report_count += 1

print(f"{perf_report_count},{metric_report_count},{no_metric_report_count}")
PY
)"
IFS=',' read -r PERF_REPORT_COUNT METRIC_REPORT_COUNT NO_METRIC_REPORT_COUNT <<< "$perf_counts"

if [[ -n "$JSON_OUT" ]]; then
  python3 - "$JSON_OUT" \
    "$WORKFLOW" "$BRANCH" "$CONCLUSION" "$MAX_RUN_AGE_DAYS" "$ARTIFACT_NAME" \
    "$DOWNLOAD_RETRIES" "$DOWNLOAD_RETRY_DELAY_SEC" \
    "$LIMIT" "$TREND_OUT" "$summary_dir" \
    "$downloaded" "$skipped" "$INCLUDE_EMPTY" "$RUN_IDS_RAW" \
    "$FAIL_IF_NONE_DOWNLOADED" "$CLEAN_DOWNLOAD_DIR" \
    "$selected_run_ids_csv" \
    "$(printf '%s,' "${downloaded_run_ids[@]}")" \
    "$(printf '%s,' "${skipped_run_ids[@]}")" \
    "$(printf '%s,' "${run_results[@]}")" \
    "$DISCOVERED_PERF_FILES" "$NORMALIZED_PERF_FILES" \
    "$PERF_REPORT_COUNT" "$METRIC_REPORT_COUNT" "$NO_METRIC_REPORT_COUNT" \
    "$FAIL_IF_SKIPPED" \
    "$FAIL_IF_NO_RUNS" \
    "$FAIL_IF_NO_METRICS" <<'PY'
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
    "discovered_perf_files": int(sys.argv[22]),
    "normalized_perf_files": int(sys.argv[23]),
    "perf_report_count": int(sys.argv[24]),
    "metric_report_count": int(sys.argv[25]),
    "no_metric_report_count": int(sys.argv[26]),
    "fail_if_skipped": sys.argv[27] == "1",
    "failed_due_to_skipped": (sys.argv[27] == "1") and (int(sys.argv[13]) > 0),
    "fail_if_no_runs": sys.argv[28] == "1",
    "failed_due_to_no_runs": (sys.argv[28] == "1") and (len(split_csv(sys.argv[18])) == 0),
    "fail_if_no_metrics": sys.argv[29] == "1",
    "failed_due_to_no_metrics": (sys.argv[29] == "1") and (len(split_csv(sys.argv[18])) > 0) and (int(sys.argv[25]) == 0),
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
print(out_path)
PY
fi

echo ""
echo "Downloaded artifacts: ${downloaded}"
echo "Skipped downloads: ${skipped}"
echo "Selected runs: ${#selected_run_ids[@]}"
echo "Discovered perf files: ${DISCOVERED_PERF_FILES} (normalized copies: ${NORMALIZED_PERF_FILES})"
echo "Perf reports: ${PERF_REPORT_COUNT} (with metrics: ${METRIC_REPORT_COUNT}, no metrics: ${NO_METRIC_REPORT_COUNT})"
echo "Summary dir: ${summary_dir}"
echo "Trend report: ${TREND_OUT}"
if [[ -n "$JSON_OUT" ]]; then
  echo "JSON summary: ${JSON_OUT}"
fi
if [[ "$FAIL_IF_NO_RUNS" -eq 1 && "${#selected_run_ids[@]}" -eq 0 ]]; then
  echo "ERROR: no runs selected; failing due to --fail-if-no-runs." >&2
  exit 1
fi
if [[ "$FAIL_IF_NO_METRICS" -eq 1 && "${#selected_run_ids[@]}" -gt 0 && "$METRIC_REPORT_COUNT" -eq 0 ]]; then
  echo "ERROR: selected runs contain no perf metrics; failing due to --fail-if-no-metrics." >&2
  exit 1
fi
if [[ "$FAIL_IF_SKIPPED" -eq 1 && "$skipped" -gt 0 ]]; then
  echo "ERROR: skipped downloads detected; failing due to --fail-if-skipped." >&2
  exit 1
fi
if [[ "$FAIL_IF_NONE_DOWNLOADED" -eq 1 && "$downloaded" -eq 0 ]]; then
  echo "ERROR: no artifacts downloaded; failing due to --fail-if-none-downloaded." >&2
  exit 1
fi
