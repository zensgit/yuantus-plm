#!/usr/bin/env bash
# =============================================================================
# CAD Extractor Service Verification Script
# Verifies standalone extractor service via /api/v1/extract.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-${CAD_EXTRACTOR_BASE_URL:-}}"
PORT="${CAD_EXTRACTOR_PORT:-8200}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

COMPOSE_CMD="${COMPOSE_CMD:-docker compose}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PROFILE="${CAD_EXTRACTOR_PROFILE:-cad-extractor}"
SERVICE="${CAD_EXTRACTOR_SERVICE:-cad-extractor}"
START_SERVICE="${START_SERVICE:-1}"

AUTH_TOKEN="${CAD_EXTRACTOR_SERVICE_TOKEN:-}"

if [[ -z "$BASE_URL" ]]; then
  BASE_URL="http://127.0.0.1:${PORT}"
fi

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

compose() {
  $COMPOSE_CMD -f "$COMPOSE_FILE" --profile "$PROFILE" "$@"
}

STARTED_BY_SCRIPT=0
EXISTING_STATE=""

if [[ "$START_SERVICE" == "1" ]]; then
  RAW="$($CURL -s "$BASE_URL/health" 2>/dev/null || true)"
  HEALTH_PRECHECK="$(RAW_JSON="$RAW" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RAW_JSON", "")
try:
    data = json.loads(raw)
    print("1" if data.get("ok") else "0")
except Exception:
    print("0")
PY
)"
  if [[ "$HEALTH_PRECHECK" == "1" ]]; then
    START_SERVICE=0
  fi
fi

if [[ "$START_SERVICE" == "1" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    fail "docker not available (set START_SERVICE=0 to skip)"
  fi
  EXISTING_ID="$(compose ps -q "$SERVICE" 2>/dev/null || true)"
  if [[ -n "$EXISTING_ID" ]]; then
    EXISTING_STATE="$(docker inspect -f '{{.State.Status}}' "$EXISTING_ID" 2>/dev/null || true)"
  fi
  if [[ "$EXISTING_STATE" != "running" ]]; then
    STARTED_BY_SCRIPT=1
    YUANTUS_CAD_EXTRACTOR_PORT="$PORT" compose up -d "$SERVICE" >/dev/null
  fi
fi

cleanup() {
  if [[ -n "${TMPFILE:-}" && -f "$TMPFILE" ]]; then
    rm -f "$TMPFILE"
  fi
  if [[ "$STARTED_BY_SCRIPT" == "1" ]]; then
    compose stop "$SERVICE" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "=============================================="
echo "CAD Extractor Service Verification"
echo "BASE_URL: $BASE_URL"
echo "START_SERVICE: $START_SERVICE"
echo "=============================================="

for _ in {1..20}; do
  RAW="$($CURL -s "$BASE_URL/health" 2>/dev/null || true)"
  HEALTH="$(RAW_JSON="$RAW" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RAW_JSON", "")
try:
    data = json.loads(raw)
    print("1" if data.get("ok") else "0")
except Exception:
    print("0")
PY
)"
  if [[ "$HEALTH" == "1" ]]; then
    break
  fi
  sleep 0.3
done

if [[ "$HEALTH" != "1" ]]; then
  fail "Extractor service not healthy at $BASE_URL/health"
fi
ok "Health check"

TMPBASE="$(mktemp /tmp/yuantus_cad_extractor_service_XXXXXX)"
TMPFILE="${TMPBASE}.dwg"
mv "$TMPBASE" "$TMPFILE"
printf 'test' > "$TMPFILE"

HEADERS=()
if [[ -n "$AUTH_TOKEN" ]]; then
  HEADERS=(-H "Authorization: Bearer $AUTH_TOKEN")
fi

RESP="$($CURL -X POST "$BASE_URL/api/v1/extract" \
  "${HEADERS[@]}" \
  -F "file=@$TMPFILE;filename=service_test.dwg" \
  -F "cad_format=DWG")"

VERIFY="$(RESP_JSON="$RESP" "$PY" - <<'PY'
import os, json
try:
    data = json.loads(os.environ.get("RESP_JSON", ""))
except Exception:
    print("FAIL:json")
    raise SystemExit(0)
if not data.get("ok"):
    print("FAIL:ok")
    raise SystemExit(0)
attrs = data.get("attributes") or {}
if attrs.get("file_ext") != "dwg":
    print("FAIL:ext")
    raise SystemExit(0)
if "file_size_bytes" not in attrs:
    print("FAIL:size")
    raise SystemExit(0)
print("OK")
PY
)"

if [[ "$VERIFY" != "OK" ]]; then
  echo "Response: $RESP" >&2
  fail "Extractor response validation failed"
fi

ok "Extract response"

echo ""
echo "=============================================="
echo "CAD Extractor Service Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
