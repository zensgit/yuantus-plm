#!/usr/bin/env bash
# =============================================================================
# S8 Ops Verification
# Runs quota monitoring, audit retention endpoints, and reports summary meta.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

printf "==============================================\n"
printf "S8 Ops Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Quota monitoring\n"
VERIFY_QUOTA_MONITORING=1 bash scripts/verify_quotas.sh "$BASE_URL" "$TENANT" "$ORG"

printf "\n==> Audit retention endpoints\n"
VERIFY_RETENTION_ENDPOINTS=1 bash scripts/verify_audit_logs.sh "$BASE_URL" "$TENANT" "$ORG"

printf "\n==> Reports summary meta\n"
bash scripts/verify_reports_summary.sh "$BASE_URL" "$TENANT" "$ORG"

printf "\n==============================================\n"
printf "S8 Ops Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
