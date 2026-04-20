#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev 142 stable readonly candidate
==========================================

Use this helper after `refreeze-readiness` says the current shared-dev 142 result still contains future-deadline pending approvals.

Purpose:
- keep the tracked baseline untouched
- produce a stable candidate preview that excludes time-sensitive pending items
- let operators review the candidate pack before deciding whether baseline design should switch to an overdue-only slice

Fast path:

- `bash scripts/run_p2_shared_dev_142_refreeze_candidate.sh`

Expanded command sequence:

```bash
OUTPUT_DIR="./tmp/p2-shared-dev-142-refreeze-candidate-$(date +%Y%m%d-%H%M%S)"

bash scripts/run_p2_shared_dev_142_readonly_rerun.sh \
  --output-dir "$OUTPUT_DIR/current" \
  --no-archive

python3 scripts/render_p2_shared_dev_142_refreeze_candidate.py \
  "$OUTPUT_DIR/current" \
  --output-dir "$OUTPUT_DIR/candidate" \
  --output-md "$OUTPUT_DIR/STABLE_READONLY_CANDIDATE.md" \
  --output-json "$OUTPUT_DIR/stable_readonly_candidate.json"
```

Expected outputs:

- `current/OBSERVATION_RESULT.md`
- `STABLE_READONLY_CANDIDATE.md`
- `stable_readonly_candidate.json`
- `candidate/summary.json`
- `candidate/items.json`
- `candidate/anomalies.json`
- `candidate/export.json`
- `candidate/export.csv`
- `candidate/OBSERVATION_RESULT.md`
- `candidate/OBSERVATION_EVAL.md`

Interpretation:

- if `CANDIDATE_READY=1`
  - the overdue-only candidate pack is internally consistent and no longer contains future pending approvals
- if `EXCLUDED_PENDING_COUNT>0`
  - candidate stability came from excluding time-sensitive pending items rather than waiting for the live environment to age
- this helper does **not** rewrite the tracked frozen baseline
EOF
