#!/usr/bin/env bash

set -euo pipefail

cat <<'EOF'
P2 shared-dev mode selection
============================

Run all repo-relative commands below from the Yuantus repo root.

Default rule:

- If you are not explicitly sure the environment can be reset, treat it as an existing shared-dev environment.
- Do not run bootstrap first on an unknown or in-use shared-dev environment.

Use existing shared-dev rerun when any of these is true:

- the environment already exists
- there may be existing data to preserve
- other people may already be using it
- you do not have explicit approval to reinitialize bootstrap fixtures

Then use:

- docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md
- bash scripts/print_p2_shared_dev_observation_commands.sh

If the environment is the current official readonly baseline on shared-dev host `142.171.239.56`, prefer:

- bash scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh

Use first-run bootstrap only when all of these are true:

- this is a fresh shared-dev environment, or
- the environment may be safely reset, and
- no existing data must be preserved, and
- no other users currently depend on it, and
- you have explicit approval to initialize bootstrap fixtures

Then use:

- docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md
- bash scripts/print_p2_shared_dev_first_run_commands.sh

One-line decision:

- not sure whether reset is allowed -> rerun path
- sure reset is allowed -> first-run path
EOF
