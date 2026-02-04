#!/usr/bin/env bash
# Minimal cleanup for repo caches (excludes .venv and references/)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

echo "Cleaning __pycache__ (excluding .venv and references/)..."
find . \( -path './.venv' -o -path './references' \) -prune -o -name '__pycache__' -print -exec rm -rf {} +

echo "Cleaning .pytest_cache..."
rm -rf .pytest_cache

echo "Done."
