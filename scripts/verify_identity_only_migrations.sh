#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade verification for "identity-only migrations":
# - Core DB migrations still run via `alembic.ini` (script_location=migrations)
# - Identity DB migrations run via `alembic.identity.ini` (script_location=migrations_identity)
# - Identity DB must contain only auth_* + audit_logs (+ alembic_version, sqlite_sequence)
#
# This script is self-contained and uses fresh SQLite DB files under /tmp.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-identity-only-migrations/${timestamp}"
OUT_DIR="${OUT_DIR:-$OUT_DIR_DEFAULT}"
mkdir -p "$OUT_DIR"

log() { echo "[$(date +%H:%M:%S)] $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

PY_BIN="${PY_BIN:-${REPO_ROOT}/.venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="python3"
fi

YUANTUS_BIN="${YUANTUS_BIN:-${REPO_ROOT}/.venv/bin/yuantus}"
if [[ ! -x "$YUANTUS_BIN" ]]; then
  YUANTUS_BIN="yuantus"
fi

CORE_DB_PATH="${CORE_DB_PATH:-/tmp/yuantus_verify_core_${timestamp}.db}"
IDENTITY_DB_PATH="${IDENTITY_DB_PATH:-/tmp/yuantus_verify_identity_${timestamp}.db}"

core_db_norm="${CORE_DB_PATH#/}"
identity_db_norm="${IDENTITY_DB_PATH#/}"

CORE_DB_URL="sqlite:////${core_db_norm}"
IDENTITY_DB_URL="sqlite:////${identity_db_norm}"

rm -f "$CORE_DB_PATH" "${CORE_DB_PATH}-shm" "${CORE_DB_PATH}-wal" 2>/dev/null || true
rm -f "$IDENTITY_DB_PATH" "${IDENTITY_DB_PATH}-shm" "${IDENTITY_DB_PATH}-wal" 2>/dev/null || true

cleanup() {
  if [[ "${KEEP_DB:-0}" == "1" ]]; then
    log "KEEP_DB=1: preserve DB files:"
    log "  core: ${CORE_DB_PATH}"
    log "  identity: ${IDENTITY_DB_PATH}"
    return 0
  fi
  rm -f "$CORE_DB_PATH" "${CORE_DB_PATH}-shm" "${CORE_DB_PATH}-wal" 2>/dev/null || true
  rm -f "$IDENTITY_DB_PATH" "${IDENTITY_DB_PATH}-shm" "${IDENTITY_DB_PATH}-wal" 2>/dev/null || true
}
trap cleanup EXIT

log "Run core migrations (migrations/ via alembic.ini)"
log "  CORE_DB_URL=${CORE_DB_URL}"
"$YUANTUS_BIN" db upgrade --db-url "$CORE_DB_URL" >"${OUT_DIR}/core_upgrade.log" 2>&1 || {
  tail -n 200 "${OUT_DIR}/core_upgrade.log" >&2 || true
  fail "core migrations failed (see ${OUT_DIR}/core_upgrade.log)"
}

log "Run identity-only migrations (migrations_identity/ via alembic.identity.ini)"
log "  IDENTITY_DB_URL=${IDENTITY_DB_URL}"
YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL" \
  "$YUANTUS_BIN" db upgrade --identity-only >"${OUT_DIR}/identity_upgrade.log" 2>&1 || {
    tail -n 200 "${OUT_DIR}/identity_upgrade.log" >&2 || true
    fail "identity-only migrations failed (see ${OUT_DIR}/identity_upgrade.log)"
  }

log "Inspect tables"
"$PY_BIN" - "$CORE_DB_PATH" "$IDENTITY_DB_PATH" "$OUT_DIR" <<'PY'
import json
import sqlite3
import sys
from pathlib import Path

core_path = Path(sys.argv[1])
identity_path = Path(sys.argv[2])
out_dir = Path(sys.argv[3])

def list_tables(db_path: Path) -> list[str]:
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()

core_tables = list_tables(core_path)
identity_tables = list_tables(identity_path)

(out_dir / "core_tables.json").write_text(json.dumps(core_tables, indent=2), encoding="utf-8")
(out_dir / "identity_tables.json").write_text(json.dumps(identity_tables, indent=2), encoding="utf-8")

required_identity = {
    "alembic_version",
    "auth_credentials",
    "auth_org_memberships",
    "auth_organizations",
    "auth_tenant_quotas",
    "auth_tenants",
    "auth_users",
    "audit_logs",
}
allowed_identity = set(required_identity) | {"sqlite_sequence"}

missing = sorted(required_identity - set(identity_tables))
unexpected = sorted(set(identity_tables) - allowed_identity)

errors: list[str] = []
if missing:
    errors.append("missing required identity tables: " + ", ".join(missing))
if unexpected:
    errors.append("unexpected identity tables: " + ", ".join(unexpected))

if "meta_items" in identity_tables:
    errors.append("identity DB should not contain meta_items")

if "meta_items" not in core_tables:
    errors.append("core DB missing meta_items (core migrations likely failed)")

if errors:
    raise SystemExit(" | ".join(errors))

print(f"core_tables={len(core_tables)} identity_tables={len(identity_tables)} ok=true")
PY

log "ALL CHECKS PASSED"
log "Evidence:"
log "  ${OUT_DIR}/core_upgrade.log"
log "  ${OUT_DIR}/identity_upgrade.log"
log "  ${OUT_DIR}/core_tables.json"
log "  ${OUT_DIR}/identity_tables.json"

