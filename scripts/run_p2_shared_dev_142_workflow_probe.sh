#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_shared_dev_142_workflow_probe.sh [options]

Options:
  --base-url <url>            Target API base URL
                              default: http://142.171.239.56:7910
  --repo <owner/name>         Optional repository override for gh (-R)
  --ref <branch>              Ref used for workflow_dispatch
                              default: main
  --username <name>           Workflow login username when password auth is used
                              default: admin
  --environment <label>       Environment label recorded in OBSERVATION_RESULT.md
                              default: shared-dev-142-workflow-probe
  --tenant-id <id>            Tenant header value
                              default: tenant-1
  --org-id <id>               Org header value
                              default: org-1
  --company-id <id>           Optional company filter
  --eco-type <value>          Optional ECO category filter
  --eco-state <value>         Optional ECO state filter
  --deadline-from <iso>       Optional deadline lower bound filter
  --deadline-to <iso>         Optional deadline upper bound filter
  --poll-interval-sec <n>     Poll interval while discovering the run id
                              default: 5
  --max-discovery-sec <n>     Max seconds to wait for run discovery
                              default: 120
  --out-dir <path>            Local directory for summary + downloaded artifact
                              default: ./tmp/p2-shared-dev-142-workflow-probe-<timestamp>
  -h, --help                  Show help

Behavior:
  - dispatches the existing p2-observation-regression GitHub workflow against shared-dev host 142
  - uses fixed shared-dev 142 defaults for base_url, tenant_id, org_id, and environment
  - downloads the workflow artifact and writes WORKFLOW_DISPATCH_RESULT.md plus workflow_dispatch.json

Boundary:
  - this is a current-only workflow probe
  - it does not perform readonly baseline compare/evaluate against the frozen 142 baseline
  - for workflow probe + readonly compare/eval, use: bash scripts/run_p2_shared_dev_142_workflow_readonly_check.sh
  - for the direct local readonly rerun path, use: bash scripts/run_p2_shared_dev_142_readonly_rerun.sh
EOF
}

timestamp="$(date +%Y%m%d-%H%M%S)"
base_url="http://142.171.239.56:7910"
repo=""
ref="main"
username="admin"
environment_name="shared-dev-142-workflow-probe"
tenant_id="tenant-1"
org_id="org-1"
company_id=""
eco_type=""
eco_state=""
deadline_from=""
deadline_to=""
poll_interval_sec="5"
max_discovery_sec="120"
out_dir="./tmp/p2-shared-dev-142-workflow-probe-${timestamp}"

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "${value}" ]]; then
    echo "Missing value for ${flag}" >&2
    usage >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      require_value "$1" "${2:-}"
      base_url="$2"
      shift 2
      ;;
    --repo)
      require_value "$1" "${2:-}"
      repo="$2"
      shift 2
      ;;
    --ref)
      require_value "$1" "${2:-}"
      ref="$2"
      shift 2
      ;;
    --username)
      require_value "$1" "${2:-}"
      username="$2"
      shift 2
      ;;
    --environment)
      require_value "$1" "${2:-}"
      environment_name="$2"
      shift 2
      ;;
    --tenant-id)
      require_value "$1" "${2:-}"
      tenant_id="$2"
      shift 2
      ;;
    --org-id)
      require_value "$1" "${2:-}"
      org_id="$2"
      shift 2
      ;;
    --company-id)
      require_value "$1" "${2:-}"
      company_id="$2"
      shift 2
      ;;
    --eco-type)
      require_value "$1" "${2:-}"
      eco_type="$2"
      shift 2
      ;;
    --eco-state)
      require_value "$1" "${2:-}"
      eco_state="$2"
      shift 2
      ;;
    --deadline-from)
      require_value "$1" "${2:-}"
      deadline_from="$2"
      shift 2
      ;;
    --deadline-to)
      require_value "$1" "${2:-}"
      deadline_to="$2"
      shift 2
      ;;
    --poll-interval-sec)
      require_value "$1" "${2:-}"
      poll_interval_sec="$2"
      shift 2
      ;;
    --max-discovery-sec)
      require_value "$1" "${2:-}"
      max_discovery_sec="$2"
      shift 2
      ;;
    --out-dir)
      require_value "$1" "${2:-}"
      out_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

echo "== Shared-dev 142 workflow probe =="
echo "BASE_URL=${base_url}"
echo "TENANT_ID=${tenant_id}"
echo "ORG_ID=${org_id}"
echo "ENVIRONMENT=${environment_name}"
echo "OUT_DIR=${out_dir}"
echo "NOTE=current-only workflow probe; readonly baseline compare remains local-wrapper only"
echo

cmd=(
  bash
  scripts/run_p2_observation_regression_workflow.sh
  --base-url "${base_url}"
  --tenant-id "${tenant_id}"
  --org-id "${org_id}"
  --username "${username}"
  --environment "${environment_name}"
  --poll-interval-sec "${poll_interval_sec}"
  --max-discovery-sec "${max_discovery_sec}"
  --out-dir "${out_dir}"
)

if [[ -n "${repo}" ]]; then
  cmd+=(--repo "${repo}")
fi
if [[ -n "${ref}" ]]; then
  cmd+=(--ref "${ref}")
fi
if [[ -n "${company_id}" ]]; then
  cmd+=(--company-id "${company_id}")
fi
if [[ -n "${eco_type}" ]]; then
  cmd+=(--eco-type "${eco_type}")
fi
if [[ -n "${eco_state}" ]]; then
  cmd+=(--eco-state "${eco_state}")
fi
if [[ -n "${deadline_from}" ]]; then
  cmd+=(--deadline-from "${deadline_from}")
fi
if [[ -n "${deadline_to}" ]]; then
  cmd+=(--deadline-to "${deadline_to}")
fi

"${cmd[@]}"
