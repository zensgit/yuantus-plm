#!/usr/bin/env bash
# =============================================================================
# CAD Connector Stub Verification Script
# Verifies: health -> capabilities -> convert -> artifacts -> (optional) job
# =============================================================================
set -euo pipefail

BASE_URL="${1:-}"
PORT="${CAD_CONNECTOR_PORT:-8300}"
HOST="${CAD_CONNECTOR_HOST:-127.0.0.1}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
START_SERVICE="${START_SERVICE:-1}"
APP_DIR="${CAD_CONNECTOR_APP_DIR:-/Users/huazhou/Downloads/Github/Yuantus/services/cad-connector}"
LOG_FILE="${CAD_CONNECTOR_LOG:-/tmp/yuantus_cad_connector_stub.log}"
PID_FILE="${CAD_CONNECTOR_PIDFILE:-/tmp/yuantus_cad_connector_stub.pid}"
AUTH_TOKEN="${CAD_CONNECTOR_SERVICE_TOKEN:-}"

if [[ -z "$BASE_URL" ]]; then
  BASE_URL="http://${HOST}:${PORT}"
fi

if [[ ! -x "$PY" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "Missing python3 (set PY=...)" >&2
    exit 2
  fi
fi

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

health_ok() {
  local raw
  raw="$($CURL "$BASE_URL/health" 2>/dev/null || true)"
  RAW_JSON="$raw" "$PY" - <<'PY'
import json
import os
raw = os.environ.get("RAW_JSON", "")
try:
    data = json.loads(raw)
    print("1" if data.get("ok") else "0")
except Exception:
    print("0")
PY
}

STARTED_BY_SCRIPT=0
if [[ "$START_SERVICE" == "1" ]]; then
  if [[ "$(health_ok)" != "1" ]]; then
    if [[ -f "$PID_FILE" ]]; then
      rm -f "$PID_FILE"
    fi
    "$PY" -m uvicorn app:app --app-dir "$APP_DIR" --host "$HOST" --port "$PORT" \
      >"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    STARTED_BY_SCRIPT=1
  fi
fi

cleanup() {
  if [[ "$STARTED_BY_SCRIPT" == "1" && -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]]; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$PID_FILE"
  fi
}
trap cleanup EXIT

for _ in {1..20}; do
  if [[ "$(health_ok)" == "1" ]]; then
    break
  fi
  sleep 0.3
done

if [[ "$(health_ok)" != "1" ]]; then
  fail "Connector stub not healthy at $BASE_URL"
fi
ok "Health check"

CAPS="$($CURL "$BASE_URL/capabilities")"
CAPS_OK="$(RAW_JSON="$CAPS" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("RAW_JSON", "")
try:
    data = json.loads(raw) if raw else {}
except Exception:
    data = {}
formats = data.get("formats") or []
print("1" if formats else "0")
PY
)"
if [[ "$CAPS_OK" != "1" ]]; then
  fail "Capabilities missing formats"
fi
ok "Capabilities"

TMPFILE="$(mktemp /tmp/yuantus_cad_connector_stub_XXXXXX.step)"
printf 'stub' > "$TMPFILE"

AUTH_HEADER=()
if [[ -n "$AUTH_TOKEN" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $AUTH_TOKEN")
fi

RESP="$($CURL -X POST "$BASE_URL/convert" \
  "${AUTH_HEADER[@]}" \
  -F "file=@$TMPFILE;filename=sample.step" \
  -F "mode=all" \
  -F "format=STEP")"

rm -f "$TMPFILE"

PARSED="$(RAW_JSON="$RESP" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("RAW_JSON", "")
try:
    data = json.loads(raw)
except Exception:
    print("FAIL parse")
    raise SystemExit(0)

if not data.get("ok"):
    print("FAIL ok")
    raise SystemExit(0)

art = data.get("artifacts") or {}
geom = art.get("geometry") or {}
prev = art.get("preview") or {}
attrs = art.get("attributes") or {}
if not geom.get("gltf_url") or not prev.get("png_url"):
    print("FAIL urls")
    raise SystemExit(0)
if not attrs.get("part_number"):
    print("FAIL attrs")
    raise SystemExit(0)

print("OK")
print(geom.get("gltf_url"))
print(prev.get("png_url"))
print(data.get("job_id") or "")
PY
)"

STATUS_LINE="$(echo "$PARSED" | head -n1)"
if [[ "$STATUS_LINE" != "OK" ]]; then
  echo "Response: $RESP" >&2
  fail "Convert response invalid"
fi

GLTF_URL="$(echo "$PARSED" | sed -n '2p')"
PREVIEW_URL="$(echo "$PARSED" | sed -n '3p')"
JOB_ID="$(echo "$PARSED" | sed -n '4p')"

if [[ -z "$GLTF_URL" || -z "$PREVIEW_URL" ]]; then
  fail "Missing artifact URLs"
fi

GLTF_HTTP="$($CURL -o /dev/null -w '%{http_code}' "$GLTF_URL")"
if [[ "$GLTF_HTTP" != "200" ]]; then
  fail "gltf_url not reachable (HTTP $GLTF_HTTP)"
fi

PREVIEW_HTTP="$($CURL -o /dev/null -w '%{http_code}' "$PREVIEW_URL")"
if [[ "$PREVIEW_HTTP" != "200" ]]; then
  fail "preview_url not reachable (HTTP $PREVIEW_HTTP)"
fi

if [[ -n "$JOB_ID" ]]; then
  JOB_RESP="$($CURL "$BASE_URL/jobs/$JOB_ID")"
  JOB_OK="$([ -n "$JOB_RESP" ] && echo "$JOB_RESP" | "$PY" - <<'PY'
import json,sys
raw = sys.stdin.read()
try:
    data = json.loads(raw)
    print("1" if data.get("status") == "completed" else "0")
except Exception:
    print("0")
PY
)"
  if [[ "$JOB_OK" != "1" ]]; then
    fail "Job status not completed"
  fi
  ok "Job status"
fi

ok "Convert + artifacts"

echo ""
echo "=============================================="
echo "CAD Connector Stub Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
