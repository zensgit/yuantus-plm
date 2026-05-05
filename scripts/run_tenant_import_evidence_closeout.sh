#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_tenant_import_evidence_closeout.sh \
    --evidence-json PATH \
    --operator-packet-json PATH \
    --artifact-prefix PREFIX \
    [--operator-evidence-template-json PATH] \
    [--archive-json PATH] \
    [--archive-md PATH] \
    [--redaction-guard-json PATH] \
    [--redaction-guard-md PATH] \
    [--evidence-handoff-json PATH] \
    [--evidence-handoff-md PATH] \
    [--evidence-intake-json PATH] \
    [--evidence-intake-md PATH] \
    [--reviewer-packet-json PATH] \
    [--reviewer-packet-md PATH] \
    [--no-strict]

Run the DB-free P3.4 evidence closeout chain after real operator-run
PostgreSQL rehearsal evidence has already been produced and accepted.

The wrapper delegates to existing Python modules in this order:

  1. tenant_import_rehearsal_evidence_archive
  2. tenant_import_rehearsal_redaction_guard
  3. tenant_import_rehearsal_evidence_handoff
  4. tenant_import_rehearsal_evidence_intake
  5. tenant_import_rehearsal_reviewer_packet

Defaults derived from --artifact-prefix PREFIX:

  --archive-json          PREFIX_import_rehearsal_evidence_archive.json
  --archive-md            PREFIX_import_rehearsal_evidence_archive.md
  --redaction-guard-json  PREFIX_redaction_guard.json
  --redaction-guard-md    PREFIX_redaction_guard.md
  --evidence-handoff-json PREFIX_evidence_handoff.json
  --evidence-handoff-md   PREFIX_evidence_handoff.md
  --evidence-intake-json  PREFIX_evidence_intake.json
  --evidence-intake-md    PREFIX_evidence_intake.md
  --reviewer-packet-json  PREFIX_reviewer_packet.json
  --reviewer-packet-md    PREFIX_reviewer_packet.md

Safety boundary:

  - reads local JSON/Markdown artifacts only;
  - writes local JSON/Markdown closeout artifacts only;
  - does not open database connections;
  - does not run row-copy rehearsal;
  - does not accept or synthesize operator evidence;
  - does not authorize production cutover.
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

evidence_json=""
operator_packet_json=""
artifact_prefix=""
operator_evidence_template_json=""
archive_json=""
archive_md=""
redaction_guard_json=""
redaction_guard_md=""
evidence_handoff_json=""
evidence_handoff_md=""
evidence_intake_json=""
evidence_intake_md=""
reviewer_packet_json=""
reviewer_packet_md=""
strict=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --evidence-json)
      evidence_json="${2:?missing value for --evidence-json}"
      shift 2
      ;;
    --operator-packet-json)
      operator_packet_json="${2:?missing value for --operator-packet-json}"
      shift 2
      ;;
    --artifact-prefix)
      artifact_prefix="${2:?missing value for --artifact-prefix}"
      shift 2
      ;;
    --operator-evidence-template-json)
      operator_evidence_template_json="${2:?missing value for --operator-evidence-template-json}"
      shift 2
      ;;
    --archive-json)
      archive_json="${2:?missing value for --archive-json}"
      shift 2
      ;;
    --archive-md)
      archive_md="${2:?missing value for --archive-md}"
      shift 2
      ;;
    --redaction-guard-json)
      redaction_guard_json="${2:?missing value for --redaction-guard-json}"
      shift 2
      ;;
    --redaction-guard-md)
      redaction_guard_md="${2:?missing value for --redaction-guard-md}"
      shift 2
      ;;
    --evidence-handoff-json)
      evidence_handoff_json="${2:?missing value for --evidence-handoff-json}"
      shift 2
      ;;
    --evidence-handoff-md)
      evidence_handoff_md="${2:?missing value for --evidence-handoff-md}"
      shift 2
      ;;
    --evidence-intake-json)
      evidence_intake_json="${2:?missing value for --evidence-intake-json}"
      shift 2
      ;;
    --evidence-intake-md)
      evidence_intake_md="${2:?missing value for --evidence-intake-md}"
      shift 2
      ;;
    --reviewer-packet-json)
      reviewer_packet_json="${2:?missing value for --reviewer-packet-json}"
      shift 2
      ;;
    --reviewer-packet-md)
      reviewer_packet_md="${2:?missing value for --reviewer-packet-md}"
      shift 2
      ;;
    --no-strict)
      strict=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$evidence_json" || -z "$operator_packet_json" || -z "$artifact_prefix" ]]; then
  echo "error: --evidence-json, --operator-packet-json, and --artifact-prefix are required" >&2
  usage >&2
  exit 2
fi

archive_json="${archive_json:-${artifact_prefix}_import_rehearsal_evidence_archive.json}"
archive_md="${archive_md:-${artifact_prefix}_import_rehearsal_evidence_archive.md}"
redaction_guard_json="${redaction_guard_json:-${artifact_prefix}_redaction_guard.json}"
redaction_guard_md="${redaction_guard_md:-${artifact_prefix}_redaction_guard.md}"
evidence_handoff_json="${evidence_handoff_json:-${artifact_prefix}_evidence_handoff.json}"
evidence_handoff_md="${evidence_handoff_md:-${artifact_prefix}_evidence_handoff.md}"
evidence_intake_json="${evidence_intake_json:-${artifact_prefix}_evidence_intake.json}"
evidence_intake_md="${evidence_intake_md:-${artifact_prefix}_evidence_intake.md}"
reviewer_packet_json="${reviewer_packet_json:-${artifact_prefix}_reviewer_packet.json}"
reviewer_packet_md="${reviewer_packet_md:-${artifact_prefix}_reviewer_packet.md}"

if [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif [[ -x "$repo_root/.venv/bin/python" ]]; then
  python_bin="$repo_root/.venv/bin/python"
else
  python_bin="python"
fi

strict_args=()
if [[ "$strict" -eq 1 ]]; then
  strict_args=(--strict)
fi

archive_args=(
  -m yuantus.scripts.tenant_import_rehearsal_evidence_archive
  --evidence-json "$evidence_json"
  --output-json "$archive_json"
  --output-md "$archive_md"
)
if [[ -n "$operator_evidence_template_json" ]]; then
  archive_args+=(--operator-evidence-template-json "$operator_evidence_template_json")
fi

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" "${archive_args[@]}" "${strict_args[@]}"

redaction_artifacts=()
while IFS= read -r artifact_path; do
  redaction_artifacts+=("$artifact_path")
done < <(
  PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" - "$archive_json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text())
for item in payload.get("artifacts") or []:
    if isinstance(item, dict) and item.get("path"):
        print(item["path"])
PY
)

redaction_args=(
  -m yuantus.scripts.tenant_import_rehearsal_redaction_guard
  --output-json "$redaction_guard_json"
  --output-md "$redaction_guard_md"
)
if [[ "${#redaction_artifacts[@]}" -gt 0 ]]; then
  for artifact in "${redaction_artifacts[@]}"; do
    redaction_args+=(--artifact "$artifact")
  done
fi

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" "${redaction_args[@]}" "${strict_args[@]}"

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" \
  -m yuantus.scripts.tenant_import_rehearsal_evidence_handoff \
  --archive-json "$archive_json" \
  --redaction-guard-json "$redaction_guard_json" \
  --output-json "$evidence_handoff_json" \
  --output-md "$evidence_handoff_md" \
  "${strict_args[@]}"

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" \
  -m yuantus.scripts.tenant_import_rehearsal_evidence_intake \
  --operator-packet-json "$operator_packet_json" \
  --output-json "$evidence_intake_json" \
  --output-md "$evidence_intake_md" \
  "${strict_args[@]}"

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" \
  -m yuantus.scripts.tenant_import_rehearsal_reviewer_packet \
  --evidence-intake-json "$evidence_intake_json" \
  --evidence-handoff-json "$evidence_handoff_json" \
  --output-json "$reviewer_packet_json" \
  --output-md "$reviewer_packet_md" \
  "${strict_args[@]}"
