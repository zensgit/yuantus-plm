# Runbook: Perf Gate Config (`configs/perf_gate.json`)

This runbook explains how to tune the **perf baseline gate** configuration used by perf CI workflows (`perf-p5-reports`, `perf-roadmap-9-3`) and how to validate changes locally.

## Where It Is Used

- Config file: `configs/perf_gate.json`
- Gate script: `scripts/perf_gate.py`
- Workflows (CI):
  - `.github/workflows/perf-p5-reports.yml`
  - `.github/workflows/perf-roadmap-9-3.yml`

In CI, workflows run the gate like:

```bash
python scripts/perf_gate.py \
  --config configs/perf_gate.json \
  --profile <profile_name> \
  --candidate <candidate_report.md> \
  --baseline-dir <baseline_dir>
```

## Config Schema (Current)

`configs/perf_gate.json` is a JSON object with:

- `version` (int): schema version (currently `1`).
- `defaults` (object): baseline window/stat and default thresholds.
  - `window` (int): number of baseline reports to use (sliding window).
  - `baseline_stat` (`"max"` or `"median"`): how to aggregate baseline values per scenario.
  - `pct` (number): allowed regression percentage (e.g. `0.30` for +30%).
  - `abs_ms` (number): allowed absolute regression in milliseconds (e.g. `10`).
- `db_overrides` (object): optional per-DB override object keyed by DB label.
  - Example key: `"postgres"`.
  - Supported fields per DB: `pct`, `abs_ms`.
- `profiles` (object): named profiles for different perf harnesses.
  - Common fields:
    - `baseline_glob` (string): which report filenames count as baselines for this harness.
  - Optional fields (same as defaults):
    - `window`, `baseline_stat`, `pct`, `abs_ms`
  - Optional per-profile overrides:
    - `db_overrides` (object): overrides/extends top-level `db_overrides` for that profile.

## DB Labels (How Overrides Match)

The gate infers a DB label from the report header line:

- `- DB: `<sqlalchemy_url>``

and maps it to a short label (examples):

- `sqlite:///...` -> `sqlite`
- `postgresql+psycopg://...` -> `postgres`

Your `db_overrides` keys must match these labels (case-insensitive).

## Precedence Rules

The effective thresholds are resolved in this order:

1. CLI flags (e.g. `--pct`, `--abs-ms`, `--window`, `--baseline-stat`)
2. Config profile fields (from `profiles.<name>.*`)
3. Config defaults (from `defaults.*`)
4. Built-in defaults in `scripts/perf_gate.py` (`window=5`, `baseline_stat=max`, `pct=0.30`, `abs_ms=10`)

DB overrides are resolved as:

1. CLI `--db-pct/--db-abs-ms` overrides
2. Config `db_overrides` (top-level + per-profile `db_overrides`)

## Common Tuning Recipes

### 1) Make the gate stricter (fewer false negatives)

- Lower `pct` and/or `abs_ms`.
- Consider `baseline_stat: "median"` if you want to be less sensitive to baseline spikes.

Example:

```json
{
  "defaults": { "pct": 0.20, "abs_ms": 5, "baseline_stat": "median", "window": 5 }
}
```

### 2) Make Postgres less noisy (fewer false positives in CI)

Keep SQLite strict, relax Postgres only:

```json
{
  "defaults": { "pct": 0.30, "abs_ms": 10 },
  "db_overrides": {
    "postgres": { "pct": 0.50, "abs_ms": 15 }
  }
}
```

### 3) Add a new perf harness profile

Add a profile with a unique report filename prefix/suffix and use it from the workflow:

```json
{
  "profiles": {
    "my_harness": { "baseline_glob": "MY_HARNESS_*.md" }
  }
}
```

Then update the workflow gate step:

```bash
python scripts/perf_gate.py --config configs/perf_gate.json --profile my_harness ...
```

## How To Validate Changes

### 1) Run unit tests (fast)

```bash
pytest -q src/yuantus/meta_engine/tests/test_perf_gate_cli.py
```

### 2) Run a local gate (example)

```bash
python scripts/perf_gate.py \
  --config configs/perf_gate.json \
  --profile roadmap_9_3 \
  --candidate docs/PERFORMANCE_REPORTS/ROADMAP_9_3_*.md \
  --baseline-dir docs/PERFORMANCE_REPORTS \
  --out tmp/perf-gate/roadmap_9_3_gate_local.txt
```

Notes:

- If no matching baselines exist, the gate will print a skip message and exit success.
- The config only sets defaults; CLI flags can always be used to experiment without editing JSON.

