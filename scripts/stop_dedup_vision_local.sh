#!/usr/bin/env bash
set -euo pipefail

DEDUP_VISION_PORT="${DEDUP_VISION_PORT:-8100}"
DEDUP_VISION_PIDFILE="${DEDUP_VISION_PIDFILE:-/tmp/dedup_vision_${DEDUP_VISION_PORT}.pid}"

if [[ ! -f "$DEDUP_VISION_PIDFILE" ]]; then
  echo "No Dedup Vision pidfile found ($DEDUP_VISION_PIDFILE)."
  exit 0
fi

vision_pid="$(cat "$DEDUP_VISION_PIDFILE" 2>/dev/null || true)"
if [[ -z "$vision_pid" ]]; then
  echo "Empty Dedup Vision pidfile."
  rm -f "$DEDUP_VISION_PIDFILE"
  exit 0
fi

if kill -0 "$vision_pid" >/dev/null 2>&1; then
  kill "$vision_pid" >/dev/null 2>&1 || true
  echo "Stopped Dedup Vision (pid=$vision_pid)."
else
  echo "Dedup Vision not running (pid=$vision_pid)."
fi

rm -f "$DEDUP_VISION_PIDFILE"
