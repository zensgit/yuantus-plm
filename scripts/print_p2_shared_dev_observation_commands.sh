#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared dev observation handoff
=================================

1. Export environment

export BASE_URL="http://<dev-host>"
export TENANT_ID="<tenant>"
export ORG_ID="<org>"

# Preferred auth:
export TOKEN="<jwt>"

# Or wrapper login fallback:
export USERNAME="admin"
export PASSWORD="<password>"

2. Run canonical shell wrapper

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)"
BASE_URL="$BASE_URL" \
TOKEN="${TOKEN:-}" \
USERNAME="${USERNAME:-}" \
PASSWORD="${PASSWORD:-}" \
TENANT_ID="$TENANT_ID" \
ORG_ID="$ORG_ID" \
ENVIRONMENT="shared-dev" \
OUTPUT_DIR="$OUTPUT_DIR" \
scripts/run_p2_observation_regression.sh

3. Optional: trigger GitHub workflow instead of local shell

scripts/run_p2_observation_regression_workflow.sh \
  --base-url "$BASE_URL" \
  --tenant-id "$TENANT_ID" \
  --org-id "$ORG_ID" \
  --environment shared-dev \
  --out-dir "./tmp/p2-observation-workflow-$(date +%Y%m%d-%H%M%S)"

4. Archive evidence to send back

tar -czf "${OUTPUT_DIR}.tar.gz" -C "$(dirname "$OUTPUT_DIR")" "$(basename "$OUTPUT_DIR")"

5. Return these files at minimum

- summary.json
- items.json
- anomalies.json
- export.csv
- README.txt
- OBSERVATION_RESULT.md

6. Optional: run raw write smoke only when explicitly allowed

BASE_URL="$BASE_URL" \
TOKEN="$TOKEN" \
TENANT_ID="$TENANT_ID" \
ORG_ID="$ORG_ID" \
RUN_WRITE_SMOKE=1 \
AUTO_ASSIGN_ECO_ID="<eco-id>" \
OUTPUT_DIR="$OUTPUT_DIR-write" \
scripts/verify_p2_dev_observation_startup.sh
EOF
