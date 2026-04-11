#!/usr/bin/env bash
# =============================================================================
# Playwright Verification: Native PLM Workspace (All)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${1:-http://127.0.0.1:7910}"

"$SCRIPT_DIR/verify_playwright_plm_workspace_documents_ui.sh" "$BASE_URL"
"$SCRIPT_DIR/verify_playwright_plm_workspace_demo_resume.sh" "$BASE_URL"
"$SCRIPT_DIR/verify_playwright_plm_workspace_document_handoff.sh" "$BASE_URL"
"$SCRIPT_DIR/verify_playwright_plm_workspace_eco_actions.sh" "$BASE_URL"
