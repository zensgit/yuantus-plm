#!/usr/bin/env bash
# =============================================================================
# Backup Rotation Verification Script
# Creates dummy backups and validates rotation keeps newest N.
# =============================================================================
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-/tmp/yuantus_backup_rotate_test}"
KEEP="${KEEP:-2}"
PREFIX="${PREFIX:-yuantus_}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

rm -rf "$BACKUP_ROOT"
mkdir -p "$BACKUP_ROOT"

for ts in 001 002 003; do
  dir="$BACKUP_ROOT/${PREFIX}${ts}"
  mkdir -p "$dir"
  echo "$ts" > "$dir/marker.txt"
  sleep 1
  done

export BACKUP_ROOT KEEP PREFIX

bash scripts/backup_rotate.sh

count=$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name "${PREFIX}*" | wc -l | xargs)
if [[ "$count" -ne "$KEEP" ]]; then
  fail "Expected $KEEP backups, got $count"
fi

newest=$(ls -1dt "$BACKUP_ROOT"/${PREFIX}* | head -n 1)
second=$(ls -1dt "$BACKUP_ROOT"/${PREFIX}* | sed -n '2p')

if ! grep -q "003" "$newest/marker.txt"; then
  fail "Newest backup not kept"
fi
if ! grep -q "002" "$second/marker.txt"; then
  fail "Second newest backup not kept"
fi

ok "Rotation kept newest $KEEP"

echo "ALL CHECKS PASSED"
