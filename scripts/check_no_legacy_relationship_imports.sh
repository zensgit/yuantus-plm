#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-src}"

if ! command -v rg >/dev/null; then
  echo "rg not found; install ripgrep to use this check." >&2
  exit 2
fi

matches=$(rg -n "relationship\\.models" "$ROOT" --glob '!**/relationship/models.py' || true)
if [[ -n "$matches" ]]; then
  echo "Found deprecated imports in $ROOT:" >&2
  echo "$matches" >&2
  exit 1
fi

echo "OK: no relationship.models imports under $ROOT"
