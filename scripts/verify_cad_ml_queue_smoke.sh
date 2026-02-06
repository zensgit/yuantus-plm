#!/usr/bin/env bash
# =============================================================================
# CAD-ML queue smoke test (cad_preview jobs, repeated)
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"
TENANCY_MODE_ENV="${TENANCY_MODE_ENV:-${YUANTUS_TENANCY_MODE:-}}"

RUN_CAD_ML_DOCKER="${RUN_CAD_ML_DOCKER:-0}"
CAD_ML_API_PORT="${CAD_ML_API_PORT:-18000}"
CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-http://127.0.0.1:${CAD_ML_API_PORT}}"
export CAD_ML_BASE_URL
export YUANTUS_CAD_ML_BASE_URL="${YUANTUS_CAD_ML_BASE_URL:-${CAD_ML_BASE_URL}}"

declare -a TMP_FILES=()

CAD_ML_QUEUE_REPEAT="${CAD_ML_QUEUE_REPEAT:-5}"
CAD_ML_QUEUE_WORKER_RUNS="${CAD_ML_QUEUE_WORKER_RUNS:-6}"
CAD_ML_QUEUE_SLEEP_SECONDS="${CAD_ML_QUEUE_SLEEP_SECONDS:-2}"
CAD_ML_QUEUE_REQUIRE_COMPLETE="${CAD_ML_QUEUE_REQUIRE_COMPLETE:-1}"
CAD_ML_QUEUE_MUTATE="${CAD_ML_QUEUE_MUTATE:-auto}"
CAD_ML_QUEUE_SAMPLE_LIST="${CAD_ML_QUEUE_SAMPLE_LIST:-}"
CAD_ML_QUEUE_CHECK_PREVIEW="${CAD_ML_QUEUE_CHECK_PREVIEW:-0}"
CAD_ML_QUEUE_PREVIEW_MIN_BYTES="${CAD_ML_QUEUE_PREVIEW_MIN_BYTES:-1}"
CAD_ML_QUEUE_PREVIEW_MIN_WIDTH="${CAD_ML_QUEUE_PREVIEW_MIN_WIDTH:-1}"
CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT="${CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT:-1}"
CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DWG="${CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DWG:-256}"
CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DWG="${CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DWG:-256}"
CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DXF="${CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DXF:-512}"
CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DXF="${CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DXF:-512}"
CAD_ML_QUEUE_STATS_CSV="${CAD_ML_QUEUE_STATS_CSV:-${REPO_ROOT}/tmp/cad_ml_queue_stats.csv}"
CAD_ML_QUEUE_STATS_CSV_ROTATE_DAYS="${CAD_ML_QUEUE_STATS_CSV_ROTATE_DAYS:-30}"

DEFAULT_SAMPLE_FILE="${REPO_ROOT}/docs/samples/cad_ml_preview_sample.dxf"
SAMPLE_FILE="${CAD_PREVIEW_SAMPLE_FILE:-$DEFAULT_SAMPLE_FILE}"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi
if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "SKIP: Sample file not found: $SAMPLE_FILE" >&2
  exit 0
fi
declare -a SAMPLE_FILES=()
if [[ -n "$CAD_ML_QUEUE_SAMPLE_LIST" ]]; then
  IFS=',' read -r -a SAMPLE_FILES <<< "$CAD_ML_QUEUE_SAMPLE_LIST"
  for i in "${!SAMPLE_FILES[@]}"; do
    sample="${SAMPLE_FILES[$i]}"
    sample="${sample#"${sample%%[![:space:]]*}"}"
    sample="${sample%"${sample##*[![:space:]]}"}"
    if [[ -z "$sample" ]]; then
      unset 'SAMPLE_FILES[i]'
      continue
    fi
    if [[ ! -f "$sample" ]]; then
      fail "Sample file not found: $sample"
    fi
    SAMPLE_FILES[$i]="$sample"
  done
fi
if [[ "${#SAMPLE_FILES[@]}" -eq 0 ]]; then
  SAMPLE_FILES=("$SAMPLE_FILE")
fi
SAMPLE_LIST_STRING=""
for sample in "${SAMPLE_FILES[@]}"; do
  if [[ -n "$SAMPLE_LIST_STRING" ]]; then
    SAMPLE_LIST_STRING+=","
  fi
  SAMPLE_LIST_STRING+="$sample"
done

CAD_ML_DOCKER_STARTED=0
cleanup_cad_ml_docker() {
  if [[ "${CAD_ML_DOCKER_STARTED:-0}" == "1" ]]; then
    echo ""
    echo "==> Stop cad-ml docker"
    "${REPO_ROOT}/scripts/stop_cad_ml_docker.sh" || true
  fi
  if [[ "${#TMP_FILES[@]}" -gt 0 ]]; then
    for tmp_file in "${TMP_FILES[@]}"; do
      rm -f "$tmp_file" || true
    done
  fi
}
trap cleanup_cad_ml_docker EXIT

if [[ "$RUN_CAD_ML_DOCKER" == "1" ]]; then
  if [[ ! -x "${REPO_ROOT}/scripts/run_cad_ml_docker.sh" || ! -x "${REPO_ROOT}/scripts/check_cad_ml_docker.sh" ]]; then
    echo "ERROR: cad-ml docker helpers not found (scripts/run_cad_ml_docker.sh)" >&2
    exit 2
  fi
  echo "==> Start cad-ml docker (RUN_CAD_ML_DOCKER=1)"
  "${REPO_ROOT}/scripts/run_cad_ml_docker.sh"
  "${REPO_ROOT}/scripts/check_cad_ml_docker.sh"
  CAD_ML_DOCKER_STARTED=1
fi

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$DB_URL" || -n "$identity_url" ]]; then
    env \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"} \
      ${TENANCY_MODE_ENV:+YUANTUS_TENANCY_MODE="$TENANCY_MODE_ENV"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

echo "=============================================="
echo "CAD-ML Queue Smoke Test"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "CAD_ML_BASE_URL: $CAD_ML_BASE_URL"
echo "REPEAT: $CAD_ML_QUEUE_REPEAT"
echo "SAMPLES: ${#SAMPLE_FILES[@]}"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login as admin"
API="$BASE_URL/api/v1"
ADMIN_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
ok "Admin login"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" -H "Authorization: Bearer $ADMIN_TOKEN")

echo ""
echo "==> Enqueue cad_preview jobs"
declare -a JOB_IDS=()
declare -a JOB_SAMPLE_EXTS=()
declare -a JOB_SAMPLE_FILES=()
QUEUE_START_TS="$(date +%s)"
for i in $(seq 1 "$CAD_ML_QUEUE_REPEAT"); do
  sample_index=$(( (i - 1) % ${#SAMPLE_FILES[@]} ))
  current_sample="${SAMPLE_FILES[$sample_index]}"
  ext="${current_sample##*.}"
  ext="${ext,,}"
  can_mutate=0
  if [[ "$CAD_ML_QUEUE_MUTATE" == "1" ]]; then
    if [[ "$ext" == "dxf" ]]; then
      can_mutate=1
    else
      echo "WARN: CAD_ML_QUEUE_MUTATE=1 ignored for .$ext (binary), using copy."
    fi
  elif [[ "$CAD_ML_QUEUE_MUTATE" == "0" ]]; then
    can_mutate=0
  else
    if [[ "$ext" == "dxf" ]]; then
      can_mutate=1
    fi
  fi
  if [[ "$can_mutate" != "1" ]]; then
    echo "WARN: Sample mutation disabled for .$ext; uploads may dedupe."
  fi
  tmp_file="$(mktemp -t "yuantus_cad_ml_queue_XXXXXX.${ext:-dxf}")"
  TMP_FILES+=("$tmp_file")
  if [[ "$can_mutate" == "1" ]]; then
    awk -v tag="$i" '{
      if ($0 == "EOF" && !done) {
        print "999"
        print "queue-smoke-" tag
        done=1
      }
      print $0
    } END {
      if (!done) {
        print "999"
        print "queue-smoke-" tag
        print "0"
        print "EOF"
      }
    }' "$current_sample" > "$tmp_file"
  else
    cp "$current_sample" "$tmp_file"
  fi
  IMPORT_RESP="$(
    $CURL -X POST "$API/cad/import" \
      "${HEADERS[@]}" \
      -F "file=@$tmp_file;filename=$(basename "$current_sample")" \
      -F 'create_preview_job=true' \
      -F 'create_geometry_job=false' \
      -F 'create_dedup_job=false' \
      -F 'create_ml_job=false' \
      -F 'create_extract_job=false'
  )"
  JOB_ID="$(
    echo "$IMPORT_RESP" | "$PY" -c '
import sys,json
d = json.load(sys.stdin)
jobs = d.get("jobs", [])
for j in jobs:
    if j.get("task_type") == "cad_preview":
        print(j.get("id") or "")
        break
'
  )"
  if [[ -z "$JOB_ID" ]]; then
    echo "Import response: $IMPORT_RESP" >&2
    fail "Missing cad_preview job id"
  fi
  JOB_IDS+=("$JOB_ID")
  JOB_SAMPLE_EXTS+=("$ext")
  JOB_SAMPLE_FILES+=("$current_sample")
  echo "Queued job $i/$CAD_ML_QUEUE_REPEAT: $JOB_ID"
done

echo ""
echo "==> Run worker to drain queue"
for i in $(seq 1 "$CAD_ML_QUEUE_WORKER_RUNS"); do
  run_cli worker --worker-id cad-ml-queue --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null || \
  run_cli worker --worker-id cad-ml-queue --poll-interval 1 --once >/dev/null

  sleep "$CAD_ML_QUEUE_SLEEP_SECONDS"

  pending=0
  for job_id in "${JOB_IDS[@]}"; do
    status="$(
      $CURL "$API/jobs/$job_id" "${HEADERS[@]}" \
        | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status","") or "")'
    )"
    if [[ "$status" == "pending" || "$status" == "processing" ]]; then
      pending=$((pending + 1))
    fi
  done
  if [[ "$pending" -eq 0 ]]; then
    break
  fi
done

echo ""
echo "==> Final job status summary"
completed=0
failed=0
cancelled=0
pending=0
processing=0
for job_id in "${JOB_IDS[@]}"; do
  status="$(
    $CURL "$API/jobs/$job_id" "${HEADERS[@]}" \
      | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status","") or "")'
  )"
  case "$status" in
    completed) completed=$((completed + 1)) ;;
    failed) failed=$((failed + 1)) ;;
    cancelled) cancelled=$((cancelled + 1)) ;;
    processing) processing=$((processing + 1)) ;;
    pending) pending=$((pending + 1)) ;;
    *) ;;
  esac
  echo "  $job_id: $status"
done

echo ""
echo "Summary:"
echo "  completed: $completed"
echo "  processing: $processing"
echo "  pending: $pending"
echo "  failed: $failed"
echo "  cancelled: $cancelled"

if [[ "$failed" -gt 0 || "$cancelled" -gt 0 ]]; then
  fail "Queue smoke failed (failed=$failed, cancelled=$cancelled)"
fi

if [[ "$CAD_ML_QUEUE_REQUIRE_COMPLETE" == "1" && ( "$pending" -gt 0 || "$processing" -gt 0 ) ]]; then
  fail "Queue smoke incomplete (pending=$pending, processing=$processing)"
fi

QUEUE_END_TS="$(date +%s)"
QUEUE_ELAPSED=$((QUEUE_END_TS - QUEUE_START_TS))
if [[ "$QUEUE_ELAPSED" -le 0 ]]; then
  QUEUE_ELAPSED=1
fi

echo ""
echo "Timing:"
echo "  elapsed_seconds: $QUEUE_ELAPSED"
avg_per_job="$( "$PY" - "$completed" "$QUEUE_ELAPSED" <<'PY'
import sys
completed = int(sys.argv[1])
elapsed = int(sys.argv[2])
if completed <= 0:
    print("0.0")
else:
    print(f"{elapsed / completed:.2f}")
PY
)"
throughput="$( "$PY" - "$completed" "$QUEUE_ELAPSED" <<'PY'
import sys
completed = int(sys.argv[1])
elapsed = int(sys.argv[2])
if completed <= 0:
    print("0.0")
else:
    print(f"{completed / (elapsed / 60):.2f}")
PY
)"
echo "  avg_seconds_per_job: $avg_per_job"
echo "  throughput_jobs_per_min: $throughput"

echo ""
echo "==> Job duration stats"
JOB_JSON_TMP="$(mktemp -t yuantus_jobs_XXXXXX.jsonl)"
TMP_FILES+=("$JOB_JSON_TMP")
for job_id in "${JOB_IDS[@]}"; do
  $CURL "$API/jobs/$job_id" "${HEADERS[@]}" \
    | "$PY" -c 'import sys,json;print(json.dumps(json.load(sys.stdin)))' \
    >> "$JOB_JSON_TMP"
done
"$PY" - "$JOB_JSON_TMP" <<'PY'
import json
import sys
from datetime import datetime

path = sys.argv[1]

def parse_dt(value):
    if not value:
        return None
    if isinstance(value, str):
        value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None

durations = []
for line in open(path, "r", encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    job = json.loads(line)
    created_at = parse_dt(job.get("created_at"))
    completed_at = parse_dt(job.get("completed_at"))
    if created_at and completed_at:
        durations.append((completed_at - created_at).total_seconds())

if durations:
    avg = sum(durations) / len(durations)
    min_d = min(durations)
    max_d = max(durations)
    print(f"  avg_job_duration_seconds: {avg:.2f}")
    print(f"  min_job_duration_seconds: {min_d:.2f}")
    print(f"  max_job_duration_seconds: {max_d:.2f}")
else:
    print("  avg_job_duration_seconds: n/a")
PY

if [[ -n "$CAD_ML_QUEUE_STATS_CSV" ]]; then
  "$PY" - "$CAD_ML_QUEUE_STATS_CSV" "$JOB_JSON_TMP" "$QUEUE_START_TS" "$QUEUE_END_TS" \
    "$QUEUE_ELAPSED" "$completed" "$failed" "$cancelled" "$pending" "$processing" \
    "$CAD_ML_QUEUE_REPEAT" "$CAD_ML_QUEUE_WORKER_RUNS" "$CAD_ML_QUEUE_MUTATE" \
    "$CAD_ML_QUEUE_CHECK_PREVIEW" "$CAD_ML_QUEUE_PREVIEW_MIN_BYTES" \
    "$CAD_ML_QUEUE_PREVIEW_MIN_WIDTH" "$CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT" \
    "$CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DWG" "$CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DWG" \
    "$CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DXF" "$CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DXF" \
    "$CAD_ML_QUEUE_STATS_CSV_ROTATE_DAYS" "$SAMPLE_LIST_STRING" <<'PY'
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone

csv_path = sys.argv[1]
job_json_path = sys.argv[2]
queue_start_ts = int(sys.argv[3])
queue_end_ts = int(sys.argv[4])
elapsed = int(sys.argv[5])
completed = int(sys.argv[6])
failed = int(sys.argv[7])
cancelled = int(sys.argv[8])
pending = int(sys.argv[9])
processing = int(sys.argv[10])
repeat = int(sys.argv[11])
worker_runs = int(sys.argv[12])
mutate = sys.argv[13]
check_preview = sys.argv[14]
min_bytes = int(sys.argv[15])
min_w = int(sys.argv[16])
min_h = int(sys.argv[17])
min_w_dwg = sys.argv[18]
min_h_dwg = sys.argv[19]
min_w_dxf = sys.argv[20]
min_h_dxf = sys.argv[21]
rotate_days = int(sys.argv[22]) if sys.argv[22] else 0
sample_list = sys.argv[23]

durations = []
try:
    with open(job_json_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            job = json.loads(line)
            created_at = job.get("created_at")
            completed_at = job.get("completed_at")
            if not created_at or not completed_at:
                continue
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            except Exception:
                continue
            durations.append((completed_dt - created_dt).total_seconds())
except FileNotFoundError:
    pass

avg_job_duration = sum(durations) / len(durations) if durations else ""
min_job_duration = min(durations) if durations else ""
max_job_duration = max(durations) if durations else ""

avg_seconds_per_job = elapsed / completed if completed else ""
throughput_jobs_per_min = (completed / (elapsed / 60)) if completed and elapsed else ""

row = {
    "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    "queue_start_ts": queue_start_ts,
    "queue_end_ts": queue_end_ts,
    "elapsed_seconds": elapsed,
    "completed": completed,
    "failed": failed,
    "cancelled": cancelled,
    "pending": pending,
    "processing": processing,
    "avg_seconds_per_job": avg_seconds_per_job,
    "throughput_jobs_per_min": throughput_jobs_per_min,
    "avg_job_duration_seconds": avg_job_duration,
    "min_job_duration_seconds": min_job_duration,
    "max_job_duration_seconds": max_job_duration,
    "repeat": repeat,
    "worker_runs": worker_runs,
    "mutate": mutate,
    "check_preview": check_preview,
    "preview_min_bytes": min_bytes,
    "preview_min_width": min_w,
    "preview_min_height": min_h,
    "preview_min_width_dwg": min_w_dwg,
    "preview_min_height_dwg": min_h_dwg,
    "preview_min_width_dxf": min_w_dxf,
    "preview_min_height_dxf": min_h_dxf,
    "samples_count": len(sample_list.split(",")) if sample_list else 0,
    "sample_list": sample_list,
}

fieldnames = list(row.keys())

dir_name = os.path.dirname(csv_path)
if dir_name:
    os.makedirs(dir_name, exist_ok=True)

if rotate_days > 0 and os.path.exists(csv_path):
    cutoff = datetime.now(timezone.utc) - timedelta(days=rotate_days)
    filtered_rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for existing in reader:
            ts = existing.get("timestamp_utc")
            if not ts:
                filtered_rows.append(existing)
                continue
            try:
                ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts_dt.tzinfo is None:
                    ts_dt = ts_dt.replace(tzinfo=timezone.utc)
            except Exception:
                filtered_rows.append(existing)
                continue
            if ts_dt >= cutoff:
                filtered_rows.append(existing)
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        if filtered_rows:
            writer.writerows(filtered_rows)
        writer.writerow(row)
else:
    write_header = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
PY
fi

if [[ "$CAD_ML_QUEUE_CHECK_PREVIEW" == "1" ]]; then
  echo ""
  echo "==> Preview output checks"
  for idx in "${!JOB_IDS[@]}"; do
    job_id="${JOB_IDS[$idx]}"
    ext="${JOB_SAMPLE_EXTS[$idx]}"
    min_w="$CAD_ML_QUEUE_PREVIEW_MIN_WIDTH"
    min_h="$CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT"
    if [[ "$ext" == "dwg" ]]; then
      if [[ -n "$CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DWG" ]]; then
        min_w="$CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DWG"
      fi
      if [[ -n "$CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DWG" ]]; then
        min_h="$CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DWG"
      fi
    elif [[ "$ext" == "dxf" ]]; then
      if [[ -n "$CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DXF" ]]; then
        min_w="$CAD_ML_QUEUE_PREVIEW_MIN_WIDTH_DXF"
      fi
      if [[ -n "$CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DXF" ]]; then
        min_h="$CAD_ML_QUEUE_PREVIEW_MIN_HEIGHT_DXF"
      fi
    fi
    job_json="$(
      $CURL "$API/jobs/$job_id" "${HEADERS[@]}"
    )"
    file_id="$(
      echo "$job_json" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);print((d.get("diagnostics") or {}).get("file_id",""))'
    )"
    if [[ -z "$file_id" ]]; then
      fail "Missing file_id for job $job_id"
    fi
    preview_tmp="$(mktemp -t "yuantus_preview_${job_id}_XXXXXX.png")"
    TMP_FILES+=("$preview_tmp")
    code="$(
      $CURL -o "$preview_tmp" -w "%{http_code}" "$API/file/$file_id/preview" "${HEADERS[@]}" || true
    )"
    size="$(wc -c < "$preview_tmp" | tr -d ' ')"
    if [[ "$code" != "200" ]]; then
      fail "Preview check failed for job $job_id (file $file_id): HTTP $code"
    fi
    if [[ "$size" -lt "$CAD_ML_QUEUE_PREVIEW_MIN_BYTES" ]]; then
      fail "Preview too small for job $job_id (file $file_id): ${size} bytes"
    fi
    dims="$(
      "$PY" - "$preview_tmp" "$min_w" "$min_h" <<'PY'
import struct
import sys

path = sys.argv[1]
min_w = int(sys.argv[2])
min_h = int(sys.argv[3])
with open(path, "rb") as f:
    sig = f.read(8)
    if sig != b"\x89PNG\r\n\x1a\n":
        print("bad_png_signature")
        sys.exit(1)
    length = f.read(4)
    if len(length) < 4:
        print("missing_length")
        sys.exit(1)
    (chunk_len,) = struct.unpack(">I", length)
    chunk_type = f.read(4)
    if chunk_type != b"IHDR":
        print("missing_IHDR")
        sys.exit(1)
    data = f.read(chunk_len)
    if len(data) < 8:
        print("short_IHDR")
        sys.exit(1)
    width, height = struct.unpack(">II", data[:8])
    if width < min_w or height < min_h:
        print(f"too_small:{width}x{height}")
        sys.exit(1)
    print(f"{width}x{height}")
PY
    )" || fail "Preview format check failed for job $job_id (file $file_id)"
    echo "Preview OK: job=$job_id file=$file_id bytes=$size dims=$dims"
  done
fi

ok "Queue smoke passed"
