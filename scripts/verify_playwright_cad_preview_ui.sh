#!/usr/bin/env bash
# =============================================================================
# Playwright Verification: CAD Preview UI (browser)
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
SAMPLE_FILE="${CAD_PREVIEW_SAMPLE_FILE:-docs/samples/cad_ml_preview_sample.dxf}"

if ! command -v npx >/dev/null 2>&1; then
  echo "Missing npx (node) in PATH" >&2
  exit 2
fi

if [[ ! -x "node_modules/.bin/playwright" ]]; then
  echo "Missing playwright in node_modules (run npm install)" >&2
  exit 2
fi

if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "Missing CAD preview sample: $SAMPLE_FILE" >&2
  exit 2
fi

RUN_PLAYWRIGHT_CAD_PREVIEW=1 \
CAD_PREVIEW_SAMPLE_FILE="$SAMPLE_FILE" \
BASE_URL="$BASE_URL" \
  npx playwright test playwright/tests/cad_preview_ui.spec.js
