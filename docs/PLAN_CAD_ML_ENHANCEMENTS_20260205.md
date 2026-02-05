# CAD-ML Enhancements Plan (2026-02-05)

## Goal
Increase reliability, reproducibility, and CI coverage for CAD‑ML verification in YuantusPLM.

## 7–10 Day Plan

### Day 1 — Samples + defaults
- Add a small DWG/DXF sample under `references/` (or `assets/`) with clear licensing.
- Update `scripts/verify_cad_preview_2d.sh` to use the repo sample when `CAD_PREVIEW_SAMPLE_FILE` is unset.
- Add a short note in `docs/VERIFICATION.md` for the fallback sample.

### Day 2 — Health + diagnostics
- Expand `scripts/check_cad_ml_docker.sh` to probe `/api/v1/vision/health` and `/api/v1/health` and surface both results.
- On failure, dump `docker logs` for cad‑ml containers into `/tmp/cad_ml_docker_logs_*.log`.

### Day 3 — CI quick regression
- Add a CI job to run `scripts/verify_cad_ml_quick.sh` with the repo sample.
- Archive log + cad‑ml docker logs as artifacts.

### Day 4 — Metrics smoke check
- Add a tiny `scripts/verify_cad_ml_metrics.sh` to ensure `/metrics` is reachable and contains a small set of expected metrics keys.
- Wire this into `scripts/verify_cad_ml_quick.sh` behind a `RUN_CAD_ML_METRICS=1` flag.

### Day 5 — Failure triage
- Add a `scripts/collect_cad_ml_debug.sh` helper to dump:
  - env summary,
  - docker ps + health status,
  - cad‑ml logs,
  - API health responses,
  into a timestamped bundle under `/tmp/`.

### Day 6–7 — Docs + polish
- Extend `docs/VERIFICATION.md` with a CAD‑ML troubleshooting section (most common errors + fixes).
- Add a short section to `README.md` linking the quick regression and troubleshooting steps.

### Day 8–10 — Optional (if time)
- Add a small Playwright check that verifies preview images render in the UI (if UI is in scope).
- Add a minimal load test for cad‑ml queueing (single file, repeated 5×) to catch deadlocks.

## Verification Strategy
- Always run `scripts/verify_cad_ml_quick.sh` after CAD‑ML changes.
- For larger changes, follow with `scripts/verify_all.sh` using `RUN_CAD_ML_DOCKER=1`.

## Risks / Open Questions
- Need a distributable DWG/DXF sample with license clarity.
- CI environment must allow Docker with network access for cad‑ml containers.
