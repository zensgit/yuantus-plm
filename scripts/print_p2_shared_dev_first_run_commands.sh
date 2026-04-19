#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev first-run checklist
=================================

Run all repo-relative commands below from the Yuantus repo root.

Use this sheet only after you have explicitly confirmed the shared-dev environment may be reset or initialized.
If reset approval is unknown, stop here and use:
- bash scripts/print_p2_shared_dev_mode_selection.sh
- bash scripts/print_p2_shared_dev_observation_commands.sh

0. Generate both env files locally

scripts/generate_p2_shared_dev_bootstrap_env.sh \
  --base-url "https://change-me-shared-dev-host"

# Replace change-me-shared-dev-host with the real shared-dev origin before continuing.

1. Validate both generated env files before touching the server

scripts/validate_p2_shared_dev_env.sh

2. Copy the bootstrap env onto the shared-dev server

# Example via scp; replace host and repo path:
scp "$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env" \
  <user>@<server-host>:<server-repo>/deployments/docker/shared-dev.bootstrap.env

3. On the shared-dev server, go to the repo root and run the one-shot bootstrap

# Fresh shared-dev first-run must use the tracked base compose file.
# Do not rely on any machine-local docker-compose.override.yml.

cd <server-repo>

docker compose -f docker-compose.yml --env-file ./deployments/docker/shared-dev.bootstrap.env \
  --profile bootstrap run --rm bootstrap

4. Start long-running services

docker compose -f docker-compose.yml up -d api worker

5. Basic health check

docker compose ps
curl -fsS http://127.0.0.1:7910/api/v1/health

6. On the operator machine, validate the local observation env again

scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$HOME/.config/yuantus/p2-shared-dev.env"

7. Run the cheap shared-dev precheck first

scripts/precheck_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"

8. If the precheck is green, run the canonical wrapper

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)" \
ARCHIVE_RESULT=1 \
scripts/run_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"

9. Return these artifacts at minimum

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

10. Optional non-superuser smoke reminder

# username: ops-viewer
# password: <same bootstrap viewer password>
EOF
