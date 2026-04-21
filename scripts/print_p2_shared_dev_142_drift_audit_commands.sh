#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev 142 drift audit
=============================

Run all repo-relative commands below from the Yuantus repo root.

Use this helper when:

- the readonly guard or readonly rerun reports a delta against the frozen baseline
- you need a fixed, repeatable way to capture the current drift before deciding whether to refreeze

Preferred one-command runner

- `bash scripts/run_p2_shared_dev_142_drift_audit.sh`

Baseline and labels

- baseline dir:
  - `./tmp/p2-shared-dev-observation-20260419-193242`
- baseline archive:
  - `./tmp/p2-shared-dev-observation-20260419-193242.tar.gz`
- baseline label:
  - `shared-dev-142-readonly-20260419`
- current label:
  - `current-drift-audit`

Expanded commands

ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
OUTPUT_DIR="./tmp/p2-shared-dev-142-drift-audit-$(date +%Y%m%d-%H%M%S)"
BASELINE_DIR="./tmp/p2-shared-dev-observation-20260419-193242"

bash scripts/run_p2_shared_dev_142_readonly_rerun.sh \
  --env-file "$ENV_FILE" \
  --output-dir "$OUTPUT_DIR/current" \
  --baseline-dir "$BASELINE_DIR" \
  --baseline-archive "./tmp/p2-shared-dev-observation-20260419-193242.tar.gz" \
  --baseline-label "shared-dev-142-readonly-20260419" \
  --no-archive

python3 scripts/render_p2_shared_dev_142_drift_audit.py \
  "$BASELINE_DIR" \
  "$OUTPUT_DIR/current" \
  --baseline-label "shared-dev-142-readonly-20260419" \
  --current-label "current-drift-audit" \
  --output-md "$OUTPUT_DIR/DRIFT_AUDIT.md" \
  --output-json "$OUTPUT_DIR/drift_audit.json"

tar -czf "${OUTPUT_DIR}.tar.gz" -C "$(dirname "$OUTPUT_DIR")" "$(basename "$OUTPUT_DIR")"
EOF
