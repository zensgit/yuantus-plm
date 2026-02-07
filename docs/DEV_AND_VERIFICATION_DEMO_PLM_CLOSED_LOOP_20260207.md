# Dev & Verification Report - Demo PLM Closed Loop Script (2026-02-07)

This delivery adds an API-only closed-loop demo script that produces a reproducible evidence bundle:

- EBOM -> Baseline -> MBOM -> Routing -> Diagnostics -> Release
- Release Readiness + Impact Summary + Item Cockpit
- Export bundles saved to a timestamped artifacts folder

It is designed for unattended demos and regression evidence (no UI dependency).

## Artifacts & Evidence

The demo script writes:

- Demo report: `docs/DAILY_REPORTS/DEMO_PLM_CLOSED_LOOP_<timestamp>.md`
- Artifacts directory: `tmp/demo-plm/<timestamp>/` (JSON payloads + zip bundles; intentionally not committed)

When run under strict gate (`DEMO_SCRIPT=1`), the strict gate report will include `DEMO_REPORT_PATH`.

## Implementation

- New script:
  - `scripts/demo_plm_closed_loop.sh`
- Strict gate integration (optional):
  - `scripts/strict_gate_report.sh` supports `DEMO_SCRIPT=1` to run the demo script as an additional step.

## Usage

Run the demo script directly:

```bash
bash scripts/demo_plm_closed_loop.sh
```

Run strict gate with demo step enabled:

```bash
DEMO_SCRIPT=1 scripts/strict_gate_report.sh
```

## Notes

- The demo script boots an isolated local server with its own SQLite DB, seeds identity/meta, runs the scenario, and shuts the server down.
- Artifacts (JSON payloads + zip bundles) are written under `tmp/demo-plm/<timestamp>/` and are intentionally not committed.
