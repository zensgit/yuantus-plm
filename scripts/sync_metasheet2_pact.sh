#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: sync_metasheet2_pact.sh [--check] [--verify-provider]

Sync the committed Metasheet2 consumer pact artifact into the Yuantus provider
repo, or check whether the local copy has drifted.

Options:
  --check            Fail if the Yuantus pact copy differs from Metasheet2.
                     Does not modify files.
  --verify-provider  After check/sync, run the local provider verifier:
                     src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
  --help             Show this help text.

Environment:
  METASHEET2_ROOT    Path to the metasheet2 checkout.
                     Default: ../metasheet2 (relative to the Yuantus repo root)
  PYTEST_BIN         Optional pytest binary for --verify-provider.
                     Default: .venv/bin/pytest
  PROVIDER_TEST      Optional provider verifier path relative to repo root.
                     Default: src/yuantus/api/tests/test_pact_provider_yuantus_plm.py

Source of truth:
  metasheet2/packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json

Target copy:
  contracts/pacts/metasheet2-yuantus-plm.json
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

hash_file() {
  local path="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
  else
    die "Need shasum or sha256sum to hash pact files"
  fi
}

CHECK_ONLY=0
VERIFY_PROVIDER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      CHECK_ONLY=1
      shift
      ;;
    --verify-provider)
      VERIFY_PROVIDER=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
METASHEET2_ROOT="${METASHEET2_ROOT:-${REPO_ROOT}/../metasheet2}"
SOURCE_RELATIVE_PATH="packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json"
TARGET_RELATIVE_PATH="contracts/pacts/metasheet2-yuantus-plm.json"
SOURCE_PATH="${METASHEET2_ROOT}/${SOURCE_RELATIVE_PATH}"
TARGET_PATH="${REPO_ROOT}/${TARGET_RELATIVE_PATH}"
PYTEST_BIN="${PYTEST_BIN:-${REPO_ROOT}/.venv/bin/pytest}"
PROVIDER_TEST="${PROVIDER_TEST:-src/yuantus/api/tests/test_pact_provider_yuantus_plm.py}"

[[ -d "${METASHEET2_ROOT}" ]] || die "METASHEET2_ROOT does not exist: ${METASHEET2_ROOT}"
[[ -f "${SOURCE_PATH}" ]] || die "Missing Metasheet2 pact source: ${SOURCE_PATH}"
[[ -f "${TARGET_PATH}" ]] || die "Missing Yuantus pact target: ${TARGET_PATH}"

SOURCE_HASH="$(hash_file "${SOURCE_PATH}")"
TARGET_HASH="$(hash_file "${TARGET_PATH}")"

if [[ "${CHECK_ONLY}" == "1" ]]; then
  if cmp -s "${SOURCE_PATH}" "${TARGET_PATH}"; then
    echo "pact_sync=ok source_hash=${SOURCE_HASH} target_hash=${TARGET_HASH}"
  else
    echo "pact_sync=drift source_hash=${SOURCE_HASH} target_hash=${TARGET_HASH}" >&2
    echo "source=${SOURCE_PATH}" >&2
    echo "target=${TARGET_PATH}" >&2
    exit 1
  fi
else
  if cmp -s "${SOURCE_PATH}" "${TARGET_PATH}"; then
    echo "pact_sync=noop source_hash=${SOURCE_HASH} target_hash=${TARGET_HASH}"
  else
    cp "${SOURCE_PATH}" "${TARGET_PATH}"
    TARGET_HASH="$(hash_file "${TARGET_PATH}")"
    echo "pact_sync=updated source_hash=${SOURCE_HASH} target_hash=${TARGET_HASH}"
  fi
fi

if [[ "${VERIFY_PROVIDER}" == "1" ]]; then
  [[ -x "${PYTEST_BIN}" ]] || die "pytest not found at ${PYTEST_BIN}"
  (
    cd "${REPO_ROOT}"
    "${PYTEST_BIN}" -q "${PROVIDER_TEST}"
  )
fi
