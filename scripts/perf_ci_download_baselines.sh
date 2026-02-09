#!/usr/bin/env bash
set -euo pipefail

# Best-effort downloader for perf baseline artifacts from recent successful CI runs.
#
# This script is intended for GitHub Actions and relies on:
# - curl, jq, unzip
# - env: GITHUB_TOKEN, GITHUB_REPOSITORY
#
# Example:
#   GITHUB_TOKEN=... GITHUB_REPOSITORY=org/repo \
#     bash scripts/perf_ci_download_baselines.sh \
#       --workflow perf-p5-reports.yml \
#       --artifact perf-p5-reports-report \
#       --artifact perf-p5-reports-report-pg \
#       --baseline-runs 5 \
#       --baseline-dir tmp/perf-baseline

WORKFLOW=""
BRANCH="main"
STATUS="success"
PER_PAGE="20"
BASELINE_RUNS="5"
BASELINE_DIR="tmp/perf-baseline"
ARTIFACTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workflow)
      WORKFLOW="${2:-}"; shift 2;;
    --branch)
      BRANCH="${2:-}"; shift 2;;
    --status)
      STATUS="${2:-}"; shift 2;;
    --per-page)
      PER_PAGE="${2:-}"; shift 2;;
    --baseline-runs)
      BASELINE_RUNS="${2:-}"; shift 2;;
    --baseline-dir)
      BASELINE_DIR="${2:-}"; shift 2;;
    --artifact)
      ARTIFACTS+=("${2:-}"); shift 2;;
    -h|--help)
      cat <<'EOF'
Usage: scripts/perf_ci_download_baselines.sh --workflow <workflow.yml> --artifact <name> [--artifact <name> ...]
       [--branch main] [--status success] [--baseline-runs 5] [--baseline-dir tmp/perf-baseline]

Downloads the given artifact(s) from the latest successful runs of the given workflow on the given branch.
All downloads are best-effort: missing runs/artifacts will not fail the caller.
EOF
      exit 0;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2;;
  esac
done

if [[ -z "${WORKFLOW}" ]]; then
  echo "Missing --workflow" >&2
  exit 2
fi

if [[ "${#ARTIFACTS[@]}" -eq 0 ]]; then
  echo "Missing --artifact" >&2
  exit 2
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Missing env GITHUB_TOKEN" >&2
  exit 2
fi

if [[ -z "${GITHUB_REPOSITORY:-}" ]]; then
  echo "Missing env GITHUB_REPOSITORY" >&2
  exit 2
fi

mkdir -p "${BASELINE_DIR}"

api="https://api.github.com/repos/${GITHUB_REPOSITORY}"
echo "[baselines] workflow=${WORKFLOW} branch=${BRANCH} status=${STATUS} baseline_runs=${BASELINE_RUNS} dir=${BASELINE_DIR}"

runs_json="$(curl -fsSL \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "${api}/actions/workflows/${WORKFLOW}/runs?branch=${BRANCH}&status=${STATUS}&per_page=${PER_PAGE}" || true)"

run_ids="$(echo "${runs_json}" | jq -r '.workflow_runs[]?.id' | head -n "${BASELINE_RUNS}" || true)"
if [[ -z "${run_ids}" ]]; then
  echo "[baselines] no baseline runs found; continuing without baselines."
  exit 0
fi

for rid in ${run_ids}; do
  echo "[baselines] run=${rid}"
  artifacts_json="$(curl -fsSL \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "${api}/actions/runs/${rid}/artifacts?per_page=100" || true)"

  for aname in "${ARTIFACTS[@]}"; do
    aid="$(echo "${artifacts_json}" | jq -r --arg name "${aname}" '.artifacts[]? | select(.name==$name) | .id' | head -n 1 || true)"
    if [[ -z "${aid}" || "${aid}" == "null" ]]; then
      echo "  - artifact missing: ${aname}"
      continue
    fi

    zip_path="${BASELINE_DIR}/${rid}-${aname}.zip"
    echo "  - downloading artifact ${aname} (${aid})"
    curl -fsSL -L \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      "${api}/actions/artifacts/${aid}/zip" \
      -o "${zip_path}" || true
    unzip -q "${zip_path}" -d "${BASELINE_DIR}" || true
  done
done

echo "[baselines] downloaded files (top 50):"
(ls -1 "${BASELINE_DIR}" | head -n 50) || true

