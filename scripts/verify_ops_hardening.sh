#!/usr/bin/env bash
# =============================================================================
# Ops Hardening Verification
# Runs multi-tenancy, quotas, audit logs, ops health, and search reindex checks.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"
TENANT_B="${4:-tenant-2}"
ORG_B="${5:-org-2}"

printf "==============================================\n"
printf "Ops Hardening Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "TENANT_B: %s, ORG_B: %s\n" "$TENANT_B" "$ORG_B"
printf "==============================================\n"

printf "\n==> Multi-tenancy\n"
bash scripts/verify_multitenancy.sh "$BASE_URL" "$TENANT" "$TENANT_B" "$ORG" "$ORG_B"

printf "\n==> Quotas\n"
bash scripts/verify_quotas.sh "$BASE_URL" "$TENANT" "$ORG"

printf "\n==> Audit logs\n"
bash scripts/verify_audit_logs.sh "$BASE_URL" "$TENANT" "$ORG"

printf "\n==> Ops health\n"
bash scripts/verify_ops_health.sh "$BASE_URL" "$TENANT" "$ORG"

printf "\n==> Search reindex\n"
bash scripts/verify_search_reindex.sh "$BASE_URL" "$TENANT" "$ORG"

printf "\n==============================================\n"
printf "Ops Hardening Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
