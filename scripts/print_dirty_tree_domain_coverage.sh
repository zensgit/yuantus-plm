#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/print_dirty_tree_domain_coverage.sh [--summary | --by-domain | --unassigned]

Options:
  --summary     Print total/assigned/unassigned dirty-path coverage summary.
  --by-domain   Print per-domain matched dirty-path counts.
  --unassigned  Print dirty paths that are not covered by the declared domains.
  -h, --help    Show help.

Default output:
  Same as --summary.
EOF
}

MODE="summary"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --summary)
      MODE="summary"
      shift
      ;;
    --by-domain)
      MODE="by-domain"
      shift
      ;;
    --unassigned)
      MODE="unassigned"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOMAIN_HELPER="${SCRIPT_DIR}/print_dirty_tree_domain_commands.sh"

DOMAINS=(
  "subcontracting"
  "docs-parallel"
  "cross-domain-services"
  "migrations"
  "strict-gate"
  "delivery-pack"
)

TMPDIR_ROOT="${TMPDIR:-/tmp}"
WORKDIR="$(mktemp -d "${TMPDIR_ROOT%/}/dirty-tree-domain-coverage.XXXXXX")"
trap 'rm -rf "${WORKDIR}"' EXIT

ALL_DIRTY="${WORKDIR}/all_dirty.txt"
ASSIGNED="${WORKDIR}/assigned.txt"
UNASSIGNED="${WORKDIR}/unassigned.txt"

git -C "${REPO_ROOT}" status --porcelain=v1 \
  | sed -E 's/^...//' \
  | sed '/^$/d' \
  | sort -u > "${ALL_DIRTY}"

> "${ASSIGNED}"

for domain in "${DOMAINS[@]}"; do
  domain_file="${WORKDIR}/${domain}.txt"
  pathspecs=()

  while IFS= read -r line; do
    [[ -n "${line}" ]] || continue
    pathspecs+=("${line}")
  done < <(bash "${DOMAIN_HELPER}" --domain "${domain}")

  if [[ "${#pathspecs[@]}" -eq 0 ]]; then
    : > "${domain_file}"
    continue
  fi

  git -C "${REPO_ROOT}" status --porcelain=v1 -- "${pathspecs[@]}" \
    | sed -E 's/^...//' \
    | sed '/^$/d' \
    | sort -u > "${domain_file}"

  cat "${domain_file}" >> "${ASSIGNED}"
done

sort -u "${ASSIGNED}" -o "${ASSIGNED}"
comm -23 "${ALL_DIRTY}" "${ASSIGNED}" > "${UNASSIGNED}"

count_lines() {
  if [[ -s "$1" ]]; then
    wc -l < "$1" | tr -d ' '
  else
    echo "0"
  fi
}

if [[ "${MODE}" == "by-domain" ]]; then
  for domain in "${DOMAINS[@]}"; do
    domain_file="${WORKDIR}/${domain}.txt"
    printf '%-24s %s\n' "${domain}" "$(count_lines "${domain_file}")"
  done
  exit 0
fi

if [[ "${MODE}" == "unassigned" ]]; then
  if [[ ! -s "${UNASSIGNED}" ]]; then
    echo "All dirty paths are covered by the declared domains."
    exit 0
  fi
  cat "${UNASSIGNED}"
  exit 0
fi

TOTAL_COUNT="$(count_lines "${ALL_DIRTY}")"
ASSIGNED_COUNT="$(count_lines "${ASSIGNED}")"
UNASSIGNED_COUNT="$(count_lines "${UNASSIGNED}")"

echo "Dirty-tree domain coverage summary:"
echo "  total dirty paths: ${TOTAL_COUNT}"
echo "  assigned dirty paths: ${ASSIGNED_COUNT}"
echo "  unassigned dirty paths: ${UNASSIGNED_COUNT}"
if [[ "${UNASSIGNED_COUNT}" == "0" ]]; then
  echo "  coverage gap present: no"
else
  echo "  coverage gap present: yes"
  echo "  inspect gaps with: bash scripts/print_dirty_tree_domain_coverage.sh --unassigned"
fi
