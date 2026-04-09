#!/usr/bin/env bash
# =============================================================================
# Playwright Verification: Native PLM Workspace Demo Resume
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"

if ! command -v npx >/dev/null 2>&1; then
  echo "Missing npx (node) in PATH" >&2
  exit 2
fi

if [[ ! -x "node_modules/.bin/playwright" ]]; then
  echo "Missing playwright in node_modules (run npm install)" >&2
  exit 2
fi

BASE_URL="$BASE_URL" npx playwright test playwright/tests/plm_workspace_demo_resume.spec.js
