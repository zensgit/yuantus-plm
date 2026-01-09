#!/usr/bin/env bash
# =============================================================================
# CAD Connectors Verification (2D + optional real samples)
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

RUN_REAL="${RUN_REAL:-${RUN_CAD_CONNECTORS_REAL:-0}}"

printf "==============================================\n"
printf "CAD Connectors Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "RUN_REAL: %s\n" "$RUN_REAL"
printf "==============================================\n"

printf "\n==> 2D connectors (synthetic)\n"
bash scripts/verify_cad_connectors_2d.sh "$BASE_URL" "$TENANT" "$ORG"

if [[ "$RUN_REAL" == "1" ]]; then
  printf "\n==> 2D connectors (real samples)\n"
  bash scripts/verify_cad_connectors_real_2d.sh "$BASE_URL" "$TENANT" "$ORG"
else
  printf "\n==> 2D connectors (real samples)\n"
  printf "SKIP: set RUN_REAL=1 to enable\n"
fi

printf "\n==============================================\n"
printf "CAD Connectors Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
