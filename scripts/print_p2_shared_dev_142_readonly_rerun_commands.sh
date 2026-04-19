#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev 142 readonly rerun
================================

Run all repo-relative commands below from the Yuantus repo root.

Use this helper only for the current official readonly baseline on shared-dev host `142.171.239.56`.
If you are not explicitly sure the environment may be reset, this is the correct path.

Preferred one-command runner

- `bash scripts/run_p2_shared_dev_142_readonly_rerun.sh`

Use the expanded commands below only when you want to inspect or tweak each step manually.

Canonical readonly baseline

- baseline dir:
  - `./tmp/p2-shared-dev-observation-20260419-193242`
- baseline archive:
  - `./tmp/p2-shared-dev-observation-20260419-193242.tar.gz`
- baseline label:
  - `shared-dev-142-readonly-20260419`

Frozen metrics

- `pending_count=2`
- `overdue_count=3`
- `escalated_count=1`
- `items_count=5`
- `export_json_count=5`
- `export_csv_rows=5`
- `total_anomalies=2`
- `escalated_unresolved=1`
- `overdue_not_escalated=1`

Optional: restore the canonical baseline dir from the archived evidence

tar -xzf ./tmp/p2-shared-dev-observation-20260419-193242.tar.gz -C ./tmp

# Optional override if you restored or copied the baseline elsewhere:
export P2_SHARED_DEV_142_BASELINE_DIR=/path/to/p2-shared-dev-observation-20260419-193242

Readonly rerun sequence

ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
BASELINE_DIR="${P2_SHARED_DEV_142_BASELINE_DIR:-./tmp/p2-shared-dev-observation-20260419-193242}"
OUTPUT_DIR="./tmp/p2-shared-dev-observation-142-readonly-rerun-$(date +%Y%m%d-%H%M%S)"

scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$ENV_FILE"

OUTPUT_DIR="$OUTPUT_DIR-precheck" \
ENVIRONMENT="shared-dev-142-readonly-precheck" \
scripts/precheck_p2_observation_regression.sh \
  --env-file "$ENV_FILE"

BASELINE_DIR="$BASELINE_DIR" \
BASELINE_LABEL="shared-dev-142-readonly-20260419" \
CURRENT_LABEL="current-rerun" \
EVAL_MODE="readonly" \
ENVIRONMENT="shared-dev-142-readonly" \
ARCHIVE_RESULT=1 \
OUTPUT_DIR="$OUTPUT_DIR" \
scripts/run_p2_observation_regression.sh \
  --env-file "$ENV_FILE"
EOF
