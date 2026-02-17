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
  --workflow <name>      Workflow name/id for gh run list (default: strict-gate)
  --branch <name>        Branch filter for gh run list (default: main)
  --conclusion <v>       Filter completed runs by conclusion: any|success|failure
                         (default: any)
  --download-dir <path>  Local artifact download root
                         (default: tmp/strict-gate-artifacts/recent-perf)
  --trend-out <path>     Output trend markdown path
                         (default: <download-dir>/STRICT_GATE_PERF_TREND.md)
  --include-empty        Include NO_METRICS runs in trend output
  --repo <owner/name>    Optional GitHub repo for gh commands (-R)
  -h, --help             Show this help and exit

Examples:
  scripts/strict_gate_perf_download_and_trend.sh
  scripts/strict_gate_perf_download_and_trend.sh --limit 20 --branch main
  scripts/strict_gate_perf_download_and_trend.sh --conclusion failure --limit 10
  scripts/strict_gate_perf_download_and_trend.sh \
    --download-dir tmp/strict-gate-artifacts/perf \
    --trend-out tmp/strict-gate-artifacts/perf/STRICT_GATE_PERF_TREND.md
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LIMIT=10
WORKFLOW="strict-gate"
BRANCH="main"
CONCLUSION="any"
DOWNLOAD_DIR="${REPO_ROOT}/tmp/strict-gate-artifacts/recent-perf"
TREND_OUT=""
INCLUDE_EMPTY=0
REPO_ARG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)
      LIMIT="${2:-}"
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
    --download-dir)
      DOWNLOAD_DIR="${2:-}"
      shift 2
      ;;
    --trend-out)
      TREND_OUT="${2:-}"
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

if [[ -z "$TREND_OUT" ]]; then
  TREND_OUT="${DOWNLOAD_DIR}/STRICT_GATE_PERF_TREND.md"
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

mkdir -p "$DOWNLOAD_DIR"

LIST_LIMIT=$((LIMIT * 3))
if [[ "$LIST_LIMIT" -lt 30 ]]; then
  LIST_LIMIT=30
fi

gh_args=(run list --workflow "$WORKFLOW" --branch "$BRANCH" --limit "$LIST_LIMIT" --json databaseId,status,conclusion)
if [[ -n "$REPO_ARG" ]]; then
  gh_args+=(-R "$REPO_ARG")
fi

echo "==> Discover recent runs (workflow=${WORKFLOW}, branch=${BRANCH}, conclusion=${CONCLUSION}, limit=${LIMIT})"
run_ids="$(
  gh "${gh_args[@]}" | python3 -c '
import json
import sys

target = int(sys.argv[1])
conclusion_filter = sys.argv[2]
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
    run_id = row.get("databaseId")
    if not run_id:
        continue
    picked.append(str(run_id))
    if len(picked) >= target:
        break
print("\n".join(picked))
' "$LIMIT" "$CONCLUSION"
)"

if [[ -z "$run_ids" ]]; then
  echo "WARN: no matching runs found for workflow=${WORKFLOW} branch=${BRANCH} conclusion=${CONCLUSION}" >&2
fi

downloaded=0
skipped=0

while IFS= read -r run_id; do
  [[ -z "$run_id" ]] && continue
  echo "==> Download artifact strict-gate-perf-summary (run_id=${run_id})"
  dl_args=(run download "$run_id" -n strict-gate-perf-summary -D "$DOWNLOAD_DIR")
  if [[ -n "$REPO_ARG" ]]; then
    dl_args+=(-R "$REPO_ARG")
  fi
  if gh "${dl_args[@]}" >/dev/null 2>&1; then
    downloaded=$((downloaded + 1))
  else
    echo "WARN: unable to download strict-gate-perf-summary for run_id=${run_id}" >&2
    skipped=$((skipped + 1))
  fi
done <<< "$run_ids"

summary_dir="${DOWNLOAD_DIR}/docs/DAILY_REPORTS"
mkdir -p "$summary_dir"
mkdir -p "$(dirname "$TREND_OUT")"

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

echo ""
echo "Downloaded artifacts: ${downloaded}"
echo "Skipped downloads: ${skipped}"
echo "Summary dir: ${summary_dir}"
echo "Trend report: ${TREND_OUT}"
