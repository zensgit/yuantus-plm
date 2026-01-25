#!/usr/bin/env bash
set -euo pipefail

CADGF_ROUTER_PORT="${CADGF_ROUTER_PORT:-9000}"
CADGF_ROUTER_PIDFILE="${CADGF_ROUTER_PIDFILE:-/tmp/cadgf_router_${CADGF_ROUTER_PORT}.pid}"

if [[ ! -f "$CADGF_ROUTER_PIDFILE" ]]; then
  echo "No CADGF router pidfile found ($CADGF_ROUTER_PIDFILE)."
  exit 0
fi

router_pid="$(cat "$CADGF_ROUTER_PIDFILE" 2>/dev/null || true)"
if [[ -z "$router_pid" ]]; then
  echo "Empty CADGF router pidfile."
  rm -f "$CADGF_ROUTER_PIDFILE"
  exit 0
fi

if kill -0 "$router_pid" >/dev/null 2>&1; then
  kill "$router_pid" >/dev/null 2>&1 || true
  echo "Stopped CADGF router (pid=$router_pid)."
else
  echo "CADGF router not running (pid=$router_pid)."
fi

rm -f "$CADGF_ROUTER_PIDFILE"
