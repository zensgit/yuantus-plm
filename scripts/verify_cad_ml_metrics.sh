#!/usr/bin/env bash
# =============================================================================
# CAD-ML Metrics Smoke Check
# =============================================================================
set -euo pipefail

CAD_ML_API_METRICS_PORT="${CAD_ML_API_METRICS_PORT:-19090}"
CAD_ML_METRICS_URL="${1:-${CAD_ML_METRICS_URL:-http://127.0.0.1:${CAD_ML_API_METRICS_PORT}/metrics}}"
CAD_ML_METRICS_REQUIRED="${CAD_ML_METRICS_REQUIRED:-1}"
CAD_ML_METRICS_REQUIRED_KEYS="${CAD_ML_METRICS_REQUIRED_KEYS:-}"
CAD_ML_METRICS_MIN_LINES="${CAD_ML_METRICS_MIN_LINES:-5}"
CAD_ML_METRICS_RETRIES="${CAD_ML_METRICS_RETRIES:-10}"
CAD_ML_METRICS_SLEEP_SECONDS="${CAD_ML_METRICS_SLEEP_SECONDS:-2}"
CURL="${CURL:-curl -sS}"

TMP="$(mktemp -t cadml_metrics_XXXXXX)"
cleanup() {
  rm -f "$TMP"
}
trap cleanup EXIT

probe_metrics() {
  local code="000"
  for i in $(seq 1 "$CAD_ML_METRICS_RETRIES"); do
    code="$($CURL -o "$TMP" -w '%{http_code}' "$CAD_ML_METRICS_URL" || true)"
    if [[ "$code" == "200" ]]; then
      break
    fi
    if [[ "$i" -lt "$CAD_ML_METRICS_RETRIES" ]]; then
      sleep "$CAD_ML_METRICS_SLEEP_SECONDS"
    fi
  done
  echo "$code"
}

HTTP_CODE="$(probe_metrics)"
if [[ "$HTTP_CODE" != "200" ]]; then
  if [[ "$CAD_ML_METRICS_REQUIRED" == "1" ]]; then
    echo "FAIL: cad-ml metrics not available (HTTP $HTTP_CODE) at $CAD_ML_METRICS_URL" >&2
    head -c 400 "$TMP" >&2 || true
    echo >&2
    exit 1
  fi
  echo "SKIP: cad-ml metrics not available (HTTP $HTTP_CODE) at $CAD_ML_METRICS_URL"
  exit 0
fi

if [[ ! -s "$TMP" ]]; then
  echo "FAIL: cad-ml metrics empty response from $CAD_ML_METRICS_URL" >&2
  exit 1
fi

line_count="$(wc -l < "$TMP" | tr -d ' ')"
if [[ "$line_count" -lt "$CAD_ML_METRICS_MIN_LINES" ]]; then
  echo "FAIL: cad-ml metrics too short (lines=$line_count, min=$CAD_ML_METRICS_MIN_LINES)" >&2
  exit 1
fi

if [[ -n "$CAD_ML_METRICS_REQUIRED_KEYS" ]]; then
  missing=()
  IFS=',' read -r -a keys <<< "$CAD_ML_METRICS_REQUIRED_KEYS"
  for key in "${keys[@]}"; do
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    if [[ -z "$key" ]]; then
      continue
    fi
    if ! grep -q "$key" "$TMP"; then
      missing+=("$key")
    fi
  done
  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "FAIL: cad-ml metrics missing keys: ${missing[*]}" >&2
    exit 1
  fi
fi

echo "cad-ml metrics: ok"
echo "  url: $CAD_ML_METRICS_URL"
echo "  lines: $line_count"
