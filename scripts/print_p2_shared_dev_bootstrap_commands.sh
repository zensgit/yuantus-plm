#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev bootstrap handoff
===============================

Run all repo-relative commands below from the Yuantus repo root.

0. Preferred: generate both env files locally first

scripts/generate_p2_shared_dev_bootstrap_env.sh \
  --base-url "https://<shared-dev-host>"

scripts/validate_p2_shared_dev_env.sh

Server-side bootstrap
---------------------

1. Prepare bootstrap env

cp "$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env" \
  deployments/docker/shared-dev.bootstrap.env

# If you did not run the helper above, fall back to:
# cp deployments/docker/shared-dev.bootstrap.env.example deployments/docker/shared-dev.bootstrap.env
# then edit:
# - YUANTUS_BOOTSTRAP_ADMIN_PASSWORD
# - YUANTUS_BOOTSTRAP_VIEWER_PASSWORD

2. Run one-shot bootstrap

docker compose --env-file ./deployments/docker/shared-dev.bootstrap.env \
  --profile bootstrap run --rm bootstrap

3. Start long-running services

docker compose up -d api worker

4. Basic health check

docker compose ps
curl -fsS http://127.0.0.1:7910/api/v1/health

Operator-side observation env
-----------------------------

ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
mkdir -p "$(dirname "$ENV_FILE")"

cat > "$ENV_FILE" <<'ENVEOF'
BASE_URL="https://<shared-dev-host>"
USERNAME="admin"
PASSWORD="<same bootstrap admin password>"
TENANT_ID="tenant-1"
ORG_ID="org-1"
ENVIRONMENT="shared-dev"
ENVEOF

chmod 600 "$ENV_FILE"

scripts/validate_p2_shared_dev_env.sh --mode observation --observation-env "$ENV_FILE"

Observation execution
---------------------

scripts/precheck_p2_observation_regression.sh --env-file "$ENV_FILE"

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="$OUTPUT_DIR" ARCHIVE_RESULT=1 \
  scripts/run_p2_observation_regression.sh --env-file "$ENV_FILE"

Optional permission smoke reminder
----------------------------------

# non-superuser 403 branch account
# username: ops-viewer
# password: <same bootstrap viewer password>
EOF
