#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev 142 daily ops
===========================

Run all repo-relative commands below from the Yuantus repo root.

Use this as the maintenance-state fast path for the official shared-dev 142 readonly baseline.

Host / base URL:
- 142.171.239.56
- http://142.171.239.56:7910

Decision rule:
- green path: readonly-rerun
- if readonly-rerun fails: drift-audit
- if drift-audit still needs explanation: drift-investigation
- do not jump to refreeze / proposal during normal daily ops

1. Start with the official readonly rerun

bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun

2. If readonly-rerun fails, collect the drift summary

bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit

3. If drift-audit still needs explanation, collect the full investigation pack

bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation

4. Human decision after investigation

- if the drift is expected time drift or accepted environment drift:
  stop and decide operationally whether to keep using the current baseline or start a controlled refreeze review
- if the drift is unexpected:
  stop and investigate writers / jobs / workflow activity before any refreeze

5. Do not use these in normal daily ops

- refreeze-readiness
- refreeze-candidate
- refreeze-proposal
- first-run bootstrap

Canonical docs:
- docs/P2_SHARED_DEV_142_DAILY_OPS_CHECKLIST.md
- docs/P2_SHARED_DEV_142_DRIFT_AUDIT_CHECKLIST.md
- docs/P2_SHARED_DEV_142_DRIFT_INVESTIGATION_CHECKLIST.md
EOF
