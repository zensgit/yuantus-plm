# Dev & Verification: CI Strict Gate Scheduled Workflow

- Date: 2026-02-07
- Scope: PLM verification automation (no CAD editing work)

## What Shipped

- New GitHub Actions workflow:
  - `.github/workflows/strict-gate.yml`

## Behavior

- Triggers:
  - Daily schedule: `03:00 UTC`
  - Manual dispatch: GitHub Actions UI (`workflow_dispatch`)
- Inputs:
  - `run_demo` (default `false`): when `true`, runs `DEMO_SCRIPT=1` to include the closed-loop demo step.
- Outputs (Artifacts):
  - `strict-gate-report`: the generated strict gate markdown report.
  - `strict-gate-logs`: per-step logs from `tmp/strict-gate/...`.

## Why

- Enables unattended, evidence-grade regression verification even when developers are not at the laptop.
- Reuses the existing strict gate + Playwright API-only suite, keeping verification consistent across local + CI.

