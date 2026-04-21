#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev 142 readonly refreeze proposal
============================================

Run all repo-relative commands below from the Yuantus repo root.

Use this helper after `refreeze-candidate` has shown that the current shared-dev 142
surface can be transformed into a stable overdue-only candidate and you now want a
formal baseline-switch proposal pack.

Preferred one-command runner

- `bash scripts/run_p2_shared_dev_142_refreeze_proposal.sh`

Use the expanded commands below only when you want to inspect or tweak each step manually.

Environment

ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
OUTPUT_DIR="./tmp/p2-shared-dev-142-refreeze-proposal-$(date +%Y%m%d-%H%M%S)"
PROPOSED_LABEL="shared-dev-142-readonly-$(date +%Y%m%d)"

scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$ENV_FILE"

bash scripts/run_p2_shared_dev_142_refreeze_candidate.sh \
  --env-file "$ENV_FILE" \
  --output-dir "$OUTPUT_DIR/candidate-preview" \
  --no-archive

python3 scripts/render_p2_shared_dev_142_refreeze_proposal.py \
  "$OUTPUT_DIR/candidate-preview" \
  --output-dir "$OUTPUT_DIR/proposal" \
  --output-md "$OUTPUT_DIR/REFREEZE_PROPOSAL.md" \
  --output-json "$OUTPUT_DIR/refreeze_proposal.json" \
  --proposed-label "$PROPOSED_LABEL"

tar -czf "$OUTPUT_DIR.tar.gz" -C "$(dirname "$OUTPUT_DIR")" "$(basename "$OUTPUT_DIR")"

Expected outputs

- `candidate-preview/STABLE_READONLY_CANDIDATE.md`
- `REFREEZE_PROPOSAL.md`
- `refreeze_proposal.json`
- `proposal/<proposed-label>/summary.json`
- `proposal/<proposed-label>/items.json`
- `proposal/<proposed-label>/anomalies.json`
- `proposal/<proposed-label>/export.json`
- `proposal/<proposed-label>/export.csv`
- `proposal/<proposed-label>/OBSERVATION_RESULT.md`
- `proposal/<proposed-label>/OBSERVATION_EVAL.md`

Decision boundary

- this helper still does **not** modify the tracked baseline in-repo
- it converts a green stable candidate into a concrete baseline-switch proposal pack
- only after reviewing that proposal should a later PR update the official tracked baseline references
EOF
