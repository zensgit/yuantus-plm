#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev 142 rerun checklist
=================================

Run all repo-relative commands below from the Yuantus repo root.

Use this sheet only for the already-initialized shared-dev on:
- host: 142.171.239.56
- base URL: http://142.171.239.56:7910

If you need to reset or bootstrap the environment again, stop here and use:
- docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md
- bash scripts/print_p2_shared_dev_first_run_commands.sh

1. Validate the existing observation env

scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$HOME/.config/yuantus/p2-shared-dev.env"

2. Run the cheap precheck first

scripts/precheck_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"

3. Only if precheck is green, run the canonical wrapper

OUTPUT_DIR="./tmp/p2-shared-dev-observation-142-$(date +%Y%m%d-%H%M%S)" \
ARCHIVE_RESULT=1 \
scripts/run_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"

4. Return these artifacts at minimum

- OBSERVATION_PRECHECK.md
- observation_precheck.json
- summary_probe.json
- summary.json
- items.json
- anomalies.json
- export.csv
- README.txt
- OBSERVATION_RESULT.md
- <OUTPUT_DIR>.tar.gz

5. Expected current state on 142

- pending_count = 1
- overdue_count = 3
- escalated_count = 1
- escalated_unresolved = 1
- overdue_not_escalated = 1
EOF
