#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared dev observation handoff
=================================

1. Export environment

export BASE_URL="http://<dev-host>"
export TOKEN="<jwt>"
export TENANT_ID="<tenant>"
export ORG_ID="<org>"

2. Run read-baseline smoke

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)"
BASE_URL="$BASE_URL" \
TOKEN="$TOKEN" \
TENANT_ID="$TENANT_ID" \
ORG_ID="$ORG_ID" \
OUTPUT_DIR="$OUTPUT_DIR" \
scripts/verify_p2_dev_observation_startup.sh

3. Archive evidence to send back

tar -czf "${OUTPUT_DIR}.tar.gz" -C "$(dirname "$OUTPUT_DIR")" "$(basename "$OUTPUT_DIR")"

4. Return these files at minimum

- summary.json
- items.json
- anomalies.json
- export.csv
- README.txt

5. Optional: run write smoke only when explicitly allowed

BASE_URL="$BASE_URL" \
TOKEN="$TOKEN" \
TENANT_ID="$TENANT_ID" \
ORG_ID="$ORG_ID" \
RUN_WRITE_SMOKE=1 \
AUTO_ASSIGN_ECO_ID="<eco-id>" \
OUTPUT_DIR="$OUTPUT_DIR-write" \
scripts/verify_p2_dev_observation_startup.sh
EOF
