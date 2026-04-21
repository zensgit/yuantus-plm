#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev 142 readonly refreeze readiness
=============================================

Run all repo-relative commands below from the Yuantus repo root.

Use this helper before any readonly baseline refresh on shared-dev host `142.171.239.56`.
It answers one narrow question:

- is the current `142` observation set stable enough to freeze again?

Preferred one-command runner

- `bash scripts/run_p2_shared_dev_142_refreeze_readiness.sh`

Use the expanded commands below only when you want to inspect each step manually.

Readonly readiness sequence

ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
OUTPUT_DIR="./tmp/p2-shared-dev-142-refreeze-readiness-$(date +%Y%m%d-%H%M%S)"

scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$ENV_FILE"

bash scripts/run_p2_shared_dev_142_readonly_rerun.sh \
  --env-file "$ENV_FILE" \
  --output-dir "$OUTPUT_DIR/current" \
  --no-archive

python3 scripts/render_p2_shared_dev_142_refreeze_readiness.py \
  "$OUTPUT_DIR/current" \
  --output-md "$OUTPUT_DIR/REFREEZE_READINESS.md" \
  --output-json "$OUTPUT_DIR/refreeze_readiness.json"

Interpretation

- `REFREEZE_READY=1`
  - current shared-dev 142 looks stable enough to promote as the next tracked readonly baseline
- `REFREEZE_READY=0`
  - do not refreeze yet
  - first inspect `REFREEZE_READINESS.md`
  - especially any pending approvals whose `approval_deadline` is still in the future
EOF
