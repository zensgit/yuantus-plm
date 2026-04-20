#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev 142 drift investigation
=====================================

Run all repo-relative commands below from the Yuantus repo root.

Use this helper when:

- drift-audit already showed readonly baseline drift on `142`
- you want a repeatable evidence pack before deciding whether to refreeze
- you need the exact evidence files plus the likely write-source paths in one place

Preferred one-command runner

- `bash scripts/run_p2_shared_dev_142_drift_investigation.sh`

Expanded commands

ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
OUTPUT_DIR="./tmp/p2-shared-dev-142-drift-investigation-$(date +%Y%m%d-%H%M%S)"

bash scripts/run_p2_shared_dev_142_drift_audit.sh \
  --env-file "$ENV_FILE" \
  --output-dir "$OUTPUT_DIR/drift-audit" \
  --baseline-dir "./tmp/p2-shared-dev-observation-20260419-193242" \
  --baseline-archive "./tmp/p2-shared-dev-observation-20260419-193242.tar.gz" \
  --baseline-label "shared-dev-142-readonly-20260419" \
  --current-label "current-drift-audit" \
  --no-archive

python3 scripts/render_p2_shared_dev_142_drift_investigation.py \
  "$OUTPUT_DIR/drift-audit" \
  --output-md "$OUTPUT_DIR/DRIFT_INVESTIGATION.md" \
  --output-json "$OUTPUT_DIR/drift_investigation.json"

tar -czf "${OUTPUT_DIR}.tar.gz" -C "$(dirname "$OUTPUT_DIR")" "$(basename "$OUTPUT_DIR")"
EOF
