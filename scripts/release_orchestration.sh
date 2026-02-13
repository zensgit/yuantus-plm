#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/release_orchestration.sh plan <item_id> [options]
  scripts/release_orchestration.sh execute <item_id> [options]

Options:
  --base <url>              API base URL (default: http://127.0.0.1:7910)
  --tenant <tenant_id>      Tenant header (default: tenant-1)
  --org <org_id>            Org header (default: org-1)

  --token <jwt>             Use an existing JWT (skips login)
  --username <u>            Login username (default: admin)
  --password <p>            Login password (default: admin)

  --ruleset <ruleset_id>    Release ruleset id (default: default)
  --routing-limit <n>       Max routings to include (default: 20)
  --mbom-limit <n>          Max mboms to include (default: 20)
  --baseline-limit <n>      Max baselines to include (default: 20)

Execute-only options:
  --dry-run                 Plan only (no state changes)
  --include-baselines       Include baseline release steps (default: false)
  --no-routings             Do not include routing releases
  --no-mboms                Do not include mbom releases
  --continue-on-error       Continue when a step fails (default: false)
  --rollback-on-failure     Best-effort rollback when a step fails (default: false)
  --baseline-force          Force baseline release when diagnostics has errors (default: false)

Output:
  --out <path>              Write JSON response to this path.
                            Default: tmp/release-orchestration/<timestamp>/<plan|execute>.json

Examples:
  scripts/release_orchestration.sh plan  <item_id> --base http://127.0.0.1:7910
  scripts/release_orchestration.sh execute <item_id> --dry-run
  scripts/release_orchestration.sh execute <item_id> --include-baselines --rollback-on-failure
EOF
}

# Global help (no args required).
if [[ $# -ge 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 ]]; then
  usage >&2
  exit 2
fi

cmd="$1"
shift

item_id="$1"
shift

BASE_URL="${BASE_URL:-${BASE:-http://127.0.0.1:7910}}"
TENANT="${TENANT_ID:-${TENANT:-tenant-1}}"
ORG="${ORG_ID:-${ORG:-org-1}}"

TOKEN="${TOKEN:-}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"

RULESET_ID="default"
ROUTING_LIMIT="20"
MBOM_LIMIT="20"
BASELINE_LIMIT="20"

INCLUDE_ROUTINGS="true"
INCLUDE_MBOMS="true"
INCLUDE_BASELINES="false"
DRY_RUN="false"
CONTINUE_ON_ERROR="false"
ROLLBACK_ON_FAILURE="false"
BASELINE_FORCE="false"

OUT_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --base)
      BASE_URL="$2"; shift 2 ;;
    --tenant)
      TENANT="$2"; shift 2 ;;
    --org)
      ORG="$2"; shift 2 ;;
    --token)
      TOKEN="$2"; shift 2 ;;
    --username)
      USERNAME="$2"; shift 2 ;;
    --password)
      PASSWORD="$2"; shift 2 ;;
    --ruleset)
      RULESET_ID="$2"; shift 2 ;;
    --routing-limit)
      ROUTING_LIMIT="$2"; shift 2 ;;
    --mbom-limit)
      MBOM_LIMIT="$2"; shift 2 ;;
    --baseline-limit)
      BASELINE_LIMIT="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN="true"; shift ;;
    --include-baselines)
      INCLUDE_BASELINES="true"; shift ;;
    --no-routings)
      INCLUDE_ROUTINGS="false"; shift ;;
    --no-mboms)
      INCLUDE_MBOMS="false"; shift ;;
    --continue-on-error)
      CONTINUE_ON_ERROR="true"; shift ;;
    --rollback-on-failure)
      ROLLBACK_ON_FAILURE="true"; shift ;;
    --baseline-force)
      BASELINE_FORCE="true"; shift ;;
    --out)
      OUT_PATH="$2"; shift 2 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

PY="${PY:-python3}"

ensure_token() {
  if [[ -n "${TOKEN}" ]]; then
    return 0
  fi

  local login_json
  login_json="$(mktemp)"
  trap 'rm -f "$login_json" >/dev/null 2>&1 || true' RETURN

  local code
  code="$(
    curl -sS -o "$login_json" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/auth/login" \
      -H 'content-type: application/json' \
      -d "{\"tenant_id\":\"${TENANT}\",\"org_id\":\"${ORG}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
  )"
  if [[ "$code" != "200" ]]; then
    echo "ERROR: login failed -> HTTP ${code} (body: ${login_json})" >&2
    cat "$login_json" >&2 || true
    return 1
  fi

  TOKEN="$("$PY" - <<PY
import json
with open("${login_json}", "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
  if [[ -z "${TOKEN}" ]]; then
    echo "ERROR: failed to parse access_token from login response" >&2
    return 1
  fi
}

timestamp="$(date +%Y%m%d-%H%M%S)"
default_out_dir="tmp/release-orchestration/${timestamp}"
mkdir -p "${default_out_dir}"

if [[ -z "${OUT_PATH}" ]]; then
  OUT_PATH="${default_out_dir}/${cmd}.json"
fi

case "${cmd}" in
  plan)
    ensure_token
    auth_header=(-H "Authorization: Bearer ${TOKEN}" -H "x-tenant-id: ${TENANT}" -H "x-org-id: ${ORG}")
    url="${BASE_URL}/api/v1/release-orchestration/items/${item_id}/plan?ruleset_id=${RULESET_ID}&routing_limit=${ROUTING_LIMIT}&mbom_limit=${MBOM_LIMIT}&baseline_limit=${BASELINE_LIMIT}"
    code="$(curl -sS -o "${OUT_PATH}" -w "%{http_code}" "${url}" "${auth_header[@]}")"
    if [[ "${code}" != "200" ]]; then
      echo "ERROR: plan -> HTTP ${code} (out: ${OUT_PATH})" >&2
      exit 1
    fi

    echo "plan_ok=true out=${OUT_PATH}"
    "$PY" - "${OUT_PATH}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
steps = data.get("steps") or []
counts = {}
for s in steps:
  action = (s or {}).get("action") or "unknown"
  counts[action] = counts.get(action, 0) + 1
print("steps_total=%d" % len(steps))
for k in sorted(counts):
  print("steps_action_%s=%d" % (k, counts[k]))
PY
    ;;
  execute)
    ensure_token
    auth_header=(-H "Authorization: Bearer ${TOKEN}" -H "x-tenant-id: ${TENANT}" -H "x-org-id: ${ORG}")
    payload="$("$PY" - <<PY
import json

def to_bool(v: str) -> bool:
  return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}

req = {
  "ruleset_id": "${RULESET_ID}",
  "include_routings": to_bool("${INCLUDE_ROUTINGS}"),
  "include_mboms": to_bool("${INCLUDE_MBOMS}"),
  "include_baselines": to_bool("${INCLUDE_BASELINES}"),
  "routing_limit": int("${ROUTING_LIMIT}"),
  "mbom_limit": int("${MBOM_LIMIT}"),
  "baseline_limit": int("${BASELINE_LIMIT}"),
  "continue_on_error": to_bool("${CONTINUE_ON_ERROR}"),
  "rollback_on_failure": to_bool("${ROLLBACK_ON_FAILURE}"),
  "dry_run": to_bool("${DRY_RUN}"),
  "baseline_force": to_bool("${BASELINE_FORCE}"),
}
print(json.dumps(req, separators=(",", ":"), ensure_ascii=True))
PY
)"
    code="$(
      curl -sS -o "${OUT_PATH}" -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/release-orchestration/items/${item_id}/execute" \
        "${auth_header[@]}" \
        -H 'content-type: application/json' \
        -d "${payload}"
    )"
    if [[ "${code}" != "200" ]]; then
      echo "ERROR: execute -> HTTP ${code} (out: ${OUT_PATH})" >&2
      exit 1
    fi

    echo "execute_ok=true out=${OUT_PATH}"
    "$PY" - "${OUT_PATH}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
results = data.get("results") or []
counts = {}
failed = []
for r in results:
  status = (r or {}).get("status") or "unknown"
  counts[status] = counts.get(status, 0) + 1
  if status in {"failed", "rollback_failed"}:
    failed.append(r)
print("results_total=%d" % len(results))
for k in sorted(counts):
  print("results_status_%s=%d" % (k, counts[k]))
if failed:
  print("failed_steps=%d" % len(failed))
PY
    ;;
  *)
    echo "Unknown command: ${cmd}" >&2
    usage >&2
    exit 2
    ;;
esac
