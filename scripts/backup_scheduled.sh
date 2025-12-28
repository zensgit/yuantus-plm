#!/usr/bin/env bash
# =============================================================================
# Scheduled backup wrapper: runs backup + rotation + optional archive.
# =============================================================================
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
KEEP="${KEEP:-7}"
ARCHIVE="${ARCHIVE:-}"

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-$BACKUP_ROOT/yuantus_$TS}"

export BACKUP_DIR BACKUP_ROOT KEEP

mkdir -p "$BACKUP_ROOT"

if [[ -n "$ARCHIVE" ]]; then
  export ARCHIVE=1
fi

bash scripts/backup_private.sh
BACKUP_ROOT="$BACKUP_ROOT" KEEP="$KEEP" bash scripts/backup_rotate.sh

echo "Scheduled backup complete: $BACKUP_DIR"
