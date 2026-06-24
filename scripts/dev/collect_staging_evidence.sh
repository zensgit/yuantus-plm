#!/usr/bin/env bash
# collect_staging_evidence.sh -- operator helper for the PLM x MetaSheet staging trial gate.
#
# This script writes a redacted evidence Markdown file. It does not make missing
# staging work look green: sections without the required inputs are marked NOT RUN.
#
# Typical usage on a staging operator host:
#   STAGING_EVIDENCE_OUT=staging-evidence.md \
#   YUANTUS_BASE_URL=https://plm-staging.example.com \
#   AUTH_HEADER='Authorization: Bearer ...' \
#   PILOT_TENANT=dogfood-acme \
#   ENTITLED_TENANT=dogfood-acme \
#   UNENTITLED_TENANT=dogfood-other \
#   PART_ID=... \
#   SIGNED_LICENSE_PATH=/secure/path/vendor-license.json \
#   SEATS_SET_LICENSE_PATH=/secure/path/vendor-license-seats-2.json \
#   SEAT_CAP_EXPECTED=2 \
#   SEATS_CLEAR_LICENSE_PATH=/secure/path/vendor-license-seats-null.json \
#   ./scripts/dev/collect_staging_evidence.sh
#
# Optional SEATS_ENFORCE_CHECK_CMD / SEATS_CLEAR_CHECK_CMD are executed with
# `bash -lc`; keep credentials in environment variables, not echoed command output.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${STAGING_EVIDENCE_OUT:-${ROOT}/PLM-COLLAB-STAGING-EVIDENCE-${TS}.md}"
YUANTUS_CMD="${YUANTUS_CMD:-yuantus}"
STRICT="${STAGING_EVIDENCE_STRICT:-0}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

status_license="NOT RUN"
status_context="NOT RUN"
status_seats_set="NOT RUN"
status_seats_clear="NOT RUN"

reason_license=""
reason_context=""
reason_seats_set=""
reason_seats_clear=""

have_vars() {
  local name
  for name in "$@"; do
    if [ -z "${!name:-}" ]; then
      return 1
    fi
  done
  return 0
}

redact_stream() {
  perl -pe '
    s/(Authorization:[[:space:]]*Bearer[[:space:]]+)[^[:space:]]+/${1}<redacted>/ig;
    s/(Bearer[[:space:]]+)[A-Za-z0-9._~+\/=-]{16,}/${1}<redacted>/g;
    s/(PACT_BROKER_TOKEN=)[^[:space:]]+/${1}<redacted>/g;
    s/("license_data"[[:space:]]*:[[:space:]]*)"[^"]*"/${1}"<redacted>"/ig;
    s/(private[_ -]?key[[:space:]]*[:=][[:space:]]*)[^,[:space:]]+/${1}<redacted>/ig;
  '
}

capture() {
  local name="$1"
  shift
  local raw="${TMPDIR}/${name}.raw"
  local redacted="${TMPDIR}/${name}.txt"
  if "$@" >"${raw}" 2>&1; then
    redact_stream <"${raw}" >"${redacted}"
    return 0
  fi
  redact_stream <"${raw}" >"${redacted}"
  return 1
}

capture_shell() {
  local name="$1"
  local command="$2"
  local raw="${TMPDIR}/${name}.raw"
  local redacted="${TMPDIR}/${name}.txt"
  if bash -lc "${command}" >"${raw}" 2>&1; then
    redact_stream <"${raw}" >"${redacted}"
    return 0
  fi
  redact_stream <"${raw}" >"${redacted}"
  return 1
}

emit_file_or_reason() {
  local name="$1"
  local reason="$2"
  local file="${TMPDIR}/${name}.txt"
  if [ -s "${file}" ]; then
    cat "${file}"
  else
    printf '%s\n' "${reason}"
  fi
}

checkboxes() {
  local status="$1"
  case "${status}" in
    PASS)
      printf -- '- [x] PASS\n- [ ] FAIL\n- [ ] NOT RUN -- reason:\n'
      ;;
    FAIL)
      printf -- '- [ ] PASS\n- [x] FAIL\n- [ ] NOT RUN -- reason:\n'
      ;;
    *)
      printf -- '- [ ] PASS\n- [ ] FAIL\n- [x] NOT RUN -- reason:\n'
      ;;
  esac
}

TENANT="${PILOT_TENANT:-${ENTITLED_TENANT:-}}"
ORG="${PILOT_ORG:-${ORG_ID:-n/a}}"
YUANTUS_VERSION_VALUE="${YUANTUS_VERSION:-$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || printf '<sha or image digest>')}"
METASHEET2_VERSION_VALUE="${METASHEET2_VERSION:-<staging sha or image digest>}"
PACT_HASH_VALUE="${PACT_HASH:-5ecbe1ee...}"
LICENSE_TYPE_VALUE="${LICENSE_TYPE:-real vendor-signed}"

if have_vars SIGNED_LICENSE_PATH TENANT; then
  if capture license_import "${YUANTUS_CMD}" license import "${SIGNED_LICENSE_PATH}" \
    && capture license_status "${YUANTUS_CMD}" license status --tenant-id "${TENANT}"; then
    if grep -qiE 'license_data|private key|bearer ' "${TMPDIR}/license_status.txt"; then
      status_license="FAIL"
      reason_license="license status output contains forbidden sensitive words after redaction"
    else
      status_license="PASS"
    fi
  else
    status_license="FAIL"
    reason_license="license import or license status command failed"
  fi
else
  reason_license="set SIGNED_LICENSE_PATH and PILOT_TENANT or ENTITLED_TENANT"
fi

if have_vars YUANTUS_BASE_URL AUTH_HEADER PILOT_TENANT ENTITLED_TENANT PART_ID; then
  if capture combined_profile env \
      YUANTUS_BASE_URL="${YUANTUS_BASE_URL}" \
      YUANTUS_BASE_ONLY_URL="${YUANTUS_BASE_ONLY_URL:-}" \
      AUTH_HEADER="${AUTH_HEADER}" \
      PILOT_TENANT="${PILOT_TENANT}" \
      "${ROOT}/scripts/dev/smoke_combined_profile.sh" \
    && capture bom_review_api env \
      YUANTUS_BASE_URL="${YUANTUS_BASE_URL}" \
      AUTH_HEADER="${AUTH_HEADER}" \
      ENTITLED_TENANT="${ENTITLED_TENANT}" \
      UNENTITLED_TENANT="${UNENTITLED_TENANT:-no-such-tenant}" \
      PART_ID="${PART_ID}" \
      MISSING_PART_ID="${MISSING_PART_ID:-}" \
      "${ROOT}/scripts/dev/smoke_bom_review_api.sh"; then
    status_context="PASS"
  else
    status_context="FAIL"
    reason_context="combined profile or BOM Review smoke failed"
  fi
else
  reason_context="set YUANTUS_BASE_URL, AUTH_HEADER, PILOT_TENANT, ENTITLED_TENANT, and PART_ID"
fi

if have_vars SEATS_SET_LICENSE_PATH SEAT_CAP_EXPECTED; then
  if capture seats_set_import "${YUANTUS_CMD}" license import "${SEATS_SET_LICENSE_PATH}"; then
    if ! grep -q "TenantQuota.max_users=${SEAT_CAP_EXPECTED}" "${TMPDIR}/seats_set_import.txt"; then
      status_seats_set="FAIL"
      reason_seats_set="license import did not report expected TenantQuota.max_users=${SEAT_CAP_EXPECTED}"
    elif [ -n "${SEATS_ENFORCE_CHECK_CMD:-}" ]; then
      if capture_shell seats_enforce_check "${SEATS_ENFORCE_CHECK_CMD}"; then
        status_seats_set="PASS"
      else
        status_seats_set="FAIL"
        reason_seats_set="SEATS_ENFORCE_CHECK_CMD failed"
      fi
    else
      reason_seats_set="seat cap import passed, but SEATS_ENFORCE_CHECK_CMD was not supplied to prove N+1 provisioning blocks"
    fi
  else
    status_seats_set="FAIL"
    reason_seats_set="seat-cap license import failed"
  fi
else
  reason_seats_set="set SEATS_SET_LICENSE_PATH, SEAT_CAP_EXPECTED, and SEATS_ENFORCE_CHECK_CMD"
fi

if have_vars SEATS_CLEAR_LICENSE_PATH; then
  if capture seats_clear_import "${YUANTUS_CMD}" license import "${SEATS_CLEAR_LICENSE_PATH}"; then
    if ! grep -q "seat cap cleared" "${TMPDIR}/seats_clear_import.txt"; then
      status_seats_clear="FAIL"
      reason_seats_clear="license import did not report seat cap cleared"
    elif [ -n "${SEATS_CLEAR_CHECK_CMD:-}" ]; then
      if capture_shell seats_clear_check "${SEATS_CLEAR_CHECK_CMD}"; then
        status_seats_clear="PASS"
      else
        status_seats_clear="FAIL"
        reason_seats_clear="SEATS_CLEAR_CHECK_CMD failed"
      fi
    else
      reason_seats_clear="seat clear import passed, but SEATS_CLEAR_CHECK_CMD was not supplied to prove clear audit and N+1 provisioning"
    fi
  else
    status_seats_clear="FAIL"
    reason_seats_clear="seats:null license import failed"
  fi
else
  reason_seats_clear="set SEATS_CLEAR_LICENSE_PATH and SEATS_CLEAR_CHECK_CMD"
fi

all_pass="false"
if [ "${status_license}" = "PASS" ] && [ "${status_context}" = "PASS" ] \
  && [ "${status_seats_set}" = "PASS" ] && [ "${status_seats_clear}" = "PASS" ]; then
  all_pass="true"
fi

mkdir -p "$(dirname "${OUT}")"
{
  cat <<EOF
# PLM-Collab V1/V1.1/V2 Seats -- Staging Evidence

**Date:** $(date -u +%Y-%m-%d)
**Environment:** ${STAGING_ENVIRONMENT:-<staging host / deployment id>}
**Operator:** ${STAGING_OPERATOR:-<name>}
**Status:** $([ "${all_pass}" = "true" ] && printf 'COMPLETE' || printf 'DRAFT -- missing or failing staging evidence remains')

Generated by \`scripts/dev/collect_staging_evidence.sh\`.

Do not paste private keys, signed license payloads, bearer tokens, database URLs, raw
\`license_data\`, or PactFlow/GitHub secret values into this file.

## 1. Version Pair And Contract Pin

| Field | Value |
|---|---|
| Yuantus commit / image | \`${YUANTUS_VERSION_VALUE}\` |
| MetaSheet2 commit / image | \`${METASHEET2_VERSION_VALUE}\` |
| Pact hash | \`${PACT_HASH_VALUE}\` |
| Local pact fallback evidence | ${LOCAL_PACT_FALLBACK_EVIDENCE:-<sync_metasheet2_pact.sh --check --verify-provider output or CI URL>} |
| PactFlow broker evidence | See section 2 |
| License type | \`${LICENSE_TYPE_VALUE}\` |
| Tenant | \`${TENANT:-<tenant id>}\` |
| Org | \`${ORG}\` |

## 2. PactFlow Broker Real-Run

Evidence already available from the activated broker line:

\`\`\`text
Consumer publish:
- MetaSheet2 PR zensgit/metasheet2#3065 merged to main at bfedff511f78d3b2026a89022473a7d42bf4fc09.
- Yuantus Pact Consumer workflow run 28075321423 created Metasheet2 version
  bfedff511f78d3b2026a89022473a7d42bf4fc09 on branch main and published the pact for provider YuantusPLM.

Provider verify/publish:
- Yuantus PR #854 final verification run 28080778247 / contracts job 83134996857.
- pact_verifier_cli exit=0.
- Computer says yes.
- provider-verify rc=0 can-i-deploy rc=0.

Drift catch:
- Temporary provider drift changed features.bom_multitable.supported and
  features.bom_multitable.entitled from booleans to strings.
- Yuantus run 28080419796 / contracts job 83133857389 failed as expected:
  Boolean-vs-String mismatches, pact_verifier_cli exit=1,
  provider-verify rc=1 can-i-deploy rc=1.

Main-branch confirmation:
- Yuantus #854 squash merged at f0855650.
- Post-merge main CI run 28081796150 / contracts job 83138269775 passed.
- Broker published YuantusPLM@f0855650 on branch main with verification result 207 (success).
- pact_verifier_cli exit=0, Computer says yes, provider-verify rc=0 can-i-deploy rc=0.

Evidence doc:
- Yuantus #861 squash merged at a352baa9.
- Post-merge main CI run 28082459739 passed; contracts completed in 8m48s and included
  Pact provider verifier plus Pact broker verify/publish/can-i-deploy.
\`\`\`

Pass/fail:
- [x] PASS
- [ ] FAIL
- [ ] NOT RUN -- reason:

## 3. License Import And Status

Expected:
- \`yuantus license import <signed-license.json>\` activates \`plm.bom_multitable\` for the staging tenant.
- \`yuantus license status --tenant-id <tenant>\` reports \`bom_multitable: ENTITLED\`.
- Output does not expose \`license_data\`, private keys, public-key material, or bearer tokens.

Evidence:

\`\`\`text
EOF
  emit_file_or_reason license_import "${reason_license}"
  if [ -s "${TMPDIR}/license_status.txt" ]; then
    printf '\n'
    cat "${TMPDIR}/license_status.txt"
  fi
  cat <<EOF
\`\`\`

Pass/fail:
EOF
  checkboxes "${status_license}"
  [ -n "${reason_license}" ] && printf '%s\n' "${reason_license}"
  cat <<EOF

## 4. Capability Manifest And BOM Context

Expected:
- \`scripts/dev/smoke_combined_profile.sh\` shows health plus manifest \`.advisory:true\`
  and \`bom_multitable.supported:true\`.
- \`scripts/dev/smoke_bom_review_api.sh\` proves:
  - unentitled existing part and missing part both return \`context:null\` without existence leak;
  - entitled tenant returns \`context.part\` plus \`lines[]\`;
  - capability manifest \`entitled\` toggles true/false by tenant.

Evidence:

\`\`\`text
EOF
  emit_file_or_reason combined_profile "${reason_context}"
  if [ -s "${TMPDIR}/bom_review_api.txt" ]; then
    printf '\n'
    cat "${TMPDIR}/bom_review_api.txt"
  fi
  cat <<EOF
\`\`\`

Pass/fail:
EOF
  checkboxes "${status_context}"
  [ -n "${reason_context}" ] && printf '%s\n' "${reason_context}"
  cat <<EOF

## 5. Seats Set And Enforce

Expected when testing caps:
- \`YUANTUS_QUOTA_MODE=enforce\`.
- Import a license carrying \`seats=N\`.
- Import prints \`seat cap projected: TenantQuota.max_users=N\`.
- Provisioning the \`(N+1)\`-th user is blocked with \`429 QUOTA_EXCEEDED\`
  or soft-warning evidence if explicitly running \`soft\` mode.

Evidence:

\`\`\`text
EOF
  emit_file_or_reason seats_set_import "${reason_seats_set}"
  if [ -s "${TMPDIR}/seats_enforce_check.txt" ]; then
    printf '\n'
    cat "${TMPDIR}/seats_enforce_check.txt"
  fi
  cat <<EOF
\`\`\`

Pass/fail:
EOF
  checkboxes "${status_seats_set}"
  [ -n "${reason_seats_set}" ] && printf '%s\n' "${reason_seats_set}"
  cat <<EOF

## 6. Seats Clear

Expected:
- Re-import a license carrying explicit \`seats:null\`.
- \`TenantQuota.max_users\` is cleared.
- Audit records the cap as cleared, for example \`max_users=cleared\`.
- The previously blocked \`(N+1)\`-th user can now be provisioned.
- Contrast remains true: absent \`seats\` is no-op; \`seats:0\`/invalid is no-op.

Evidence:

\`\`\`text
EOF
  emit_file_or_reason seats_clear_import "${reason_seats_clear}"
  if [ -s "${TMPDIR}/seats_clear_check.txt" ]; then
    printf '\n'
    cat "${TMPDIR}/seats_clear_check.txt"
  fi
  cat <<EOF
\`\`\`

Pass/fail:
EOF
  checkboxes "${status_seats_clear}"
  [ -n "${reason_seats_clear}" ] && printf '%s\n' "${reason_seats_clear}"
  cat <<EOF

## 7. Explicit Untested List

EOF
  if [ "${all_pass}" = "true" ]; then
    printf -- '- None\n'
  else
    [ "${status_license}" = "PASS" ] || printf -- '- License import/status -- %s\n' "${reason_license}"
    [ "${status_context}" = "PASS" ] || printf -- '- Capability manifest and BOM context -- %s\n' "${reason_context}"
    [ "${status_seats_set}" = "PASS" ] || printf -- '- Seats set/enforce -- %s\n' "${reason_seats_set}"
    [ "${status_seats_clear}" = "PASS" ] || printf -- '- Seats clear -- %s\n' "${reason_seats_clear}"
  fi
  cat <<EOF

## 8. Trialability Decision

Decision:
EOF
  if [ "${all_pass}" = "true" ]; then
    printf -- '- [x] Trialable for the stated environment/version pair.\n- [ ] Not trialable; blocking reason:\n'
  else
    printf -- '- [ ] Trialable for the stated environment/version pair.\n- [x] Not trialable; blocking reason: required staging evidence is missing or failing.\n'
  fi
  cat <<EOF

Scope of decision:
EOF
  if [ "${all_pass}" = "true" ]; then
    printf -- '- [x] Full post-broker baseline: section 2 PactFlow broker real-run is PASS and all staging sections passed.\n'
  else
    printf -- '- [ ] Full post-broker baseline: section 2 PactFlow broker real-run is PASS, but staging sections are incomplete.\n'
  fi
  cat <<EOF
- [ ] Pre-broker staging only: section 2 is NOT RUN, and this record must not be used to claim
      PactFlow real-run completion.

Reviewer notes:

\`\`\`text
${STAGING_REVIEWER_NOTES:-<notes>}
\`\`\`
EOF
} >"${OUT}"

printf 'staging evidence written: %s\n' "${OUT}"

if [ "${STRICT}" = "1" ] && [ "${all_pass}" != "true" ]; then
  printf 'staging evidence incomplete; refusing success because STAGING_EVIDENCE_STRICT=1\n' >&2
  exit 1
fi
