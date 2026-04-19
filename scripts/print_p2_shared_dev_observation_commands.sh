#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared dev observation rerun handoff
=======================================

Run all repo-relative commands below from the Yuantus repo root.

Use this sheet only when the shared-dev environment already exists and you already have valid credentials.
For fresh shared-dev bootstrap, use:
- docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md
- bash scripts/print_p2_shared_dev_first_run_commands.sh

1. Preferred: put shared-dev defaults in a local env file

ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
mkdir -p "$(dirname "$ENV_FILE")"

cat > "$ENV_FILE" <<'ENVEOF'
BASE_URL="http://<dev-host>"
TENANT_ID="<tenant>"
ORG_ID="<org>"
TOKEN="<jwt>"
ENVIRONMENT="shared-dev"
ENVEOF

chmod 600 "$ENV_FILE"

scripts/validate_p2_shared_dev_env.sh --mode observation --observation-env "$ENV_FILE"

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)" \
scripts/precheck_p2_observation_regression.sh \
  --env-file "$ENV_FILE"

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)" \
ARCHIVE_RESULT=1 scripts/run_p2_observation_regression.sh \
  --env-file "$ENV_FILE"

2. Fallback: export environment directly

export BASE_URL="http://<dev-host>"
export TENANT_ID="<tenant>"
export ORG_ID="<org>"
export TOKEN="<jwt>"
export USERNAME="admin"
export PASSWORD="<password>"

3. Run local precheck

scripts/precheck_p2_observation_regression.sh

4. Run canonical shell wrapper

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)"
BASE_URL="$BASE_URL" \
TOKEN="${TOKEN:-}" \
USERNAME="${USERNAME:-}" \
PASSWORD="${PASSWORD:-}" \
TENANT_ID="$TENANT_ID" \
ORG_ID="$ORG_ID" \
ENVIRONMENT="shared-dev" \
ARCHIVE_RESULT=1 \
OUTPUT_DIR="$OUTPUT_DIR" \
scripts/run_p2_observation_regression.sh

5. Optional: trigger GitHub workflow instead of local shell

scripts/run_p2_observation_regression_workflow.sh \
  --base-url "$BASE_URL" \
  --tenant-id "$TENANT_ID" \
  --org-id "$ORG_ID" \
  --environment shared-dev \
  --out-dir "./tmp/p2-observation-workflow-$(date +%Y%m%d-%H%M%S)"

6. Archive evidence to send back

# If ARCHIVE_RESULT=1 was set above, this file already exists:
# "${OUTPUT_DIR}.tar.gz"

tar -czf "${OUTPUT_DIR}.tar.gz" -C "$(dirname "$OUTPUT_DIR")" "$(basename "$OUTPUT_DIR")"

7. Return these files at minimum

- OBSERVATION_PRECHECK.md
- observation_precheck.json
- summary.json
- items.json
- anomalies.json
- export.csv
- README.txt
- OBSERVATION_RESULT.md

8. Optional: run raw write smoke only when explicitly allowed

BASE_URL="$BASE_URL" \
TOKEN="$TOKEN" \
TENANT_ID="$TENANT_ID" \
ORG_ID="$ORG_ID" \
RUN_WRITE_SMOKE=1 \
AUTO_ASSIGN_ECO_ID="<eco-id>" \
OUTPUT_DIR="$OUTPUT_DIR-write" \
scripts/verify_p2_dev_observation_startup.sh
EOF
