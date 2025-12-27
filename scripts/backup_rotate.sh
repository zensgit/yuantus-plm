#!/usr/bin/env bash
# =============================================================================
# Backup rotation helper: keeps the newest N backups, deletes the rest.
# =============================================================================
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
PREFIX="${PREFIX:-yuantus_}"
KEEP="${KEEP:-7}"
DRY_RUN="${DRY_RUN:-}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

if [[ ! -d "$BACKUP_ROOT" ]]; then
  fail "Backup root not found: $BACKUP_ROOT"
fi

shopt -s nullglob
paths=("$BACKUP_ROOT"/"${PREFIX}"*)
shopt -u nullglob

if [[ ${#paths[@]} -eq 0 ]]; then
  ok "Nothing to rotate (count=0, keep=$KEEP)"
  exit 0
fi

if stat -f '%m %N' . >/dev/null 2>&1; then
  mapfile -t backups < <(
    stat -f '%m %N' "${paths[@]}" 2>/dev/null \
      | sort -nr \
      | awk '{$1=""; sub(/^ /,""); print}'
  )
else
  mapfile -t backups < <(
    stat -c '%Y %n' "${paths[@]}" 2>/dev/null \
      | sort -nr \
      | awk '{$1=""; sub(/^ /,""); print}'
  )
fi

if [[ ${#backups[@]} -le $KEEP ]]; then
  ok "Nothing to rotate (count=${#backups[@]}, keep=$KEEP)"
  exit 0
fi

echo "Keeping newest $KEEP backups, rotating ${#backups[@]} total"

idx=0
for dir in "${backups[@]}"; do
  idx=$((idx + 1))
  if [[ $idx -le $KEEP ]]; then
    echo "KEEP: $dir"
    continue
  fi
  if [[ -n "$DRY_RUN" ]]; then
    echo "DRY_RUN delete: $dir"
  else
    echo "DELETE: $dir"
    rm -rf "$dir"
  fi
  done

echo "Rotation complete."
