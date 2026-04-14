# P1 CAD PR Stabilization

Date: 2026-04-15
Branch: `baseline/mainline-20260414-150835`
PR: `#201`

## Summary

PR `#201` is now stable at the GitHub check level.

Final GitHub state:

- `mergeStateStatus = CLEAN`
- `mergeable = MERGEABLE`

Relevant checks:

- `contracts` → passed
- `plugin-tests` → passed
- `regression` → passed
- `perf-roadmap-9-3` → passed

Skipped checks remained skipped as expected:

- `cad_ml_quick`
- `cadgf_preview`
- `playwright-esign`

## What Stabilized The PR

This stabilization followed the remediation slice documented in:

- `docs/DEV_AND_VERIFICATION_P1_CAD_PR_UNSTABLE_CI_REMEDIATION_20260415.md`

The key fixes were:

1. merge main Alembic heads back to one head
2. add migration coverage for `meta_eco_routing_changes`
3. allowlist historical migration-only table `cad_conversion_jobs`
4. repair runbook/doc index contracts
5. rebuild the BOM compare plugin request model for importlib-loaded plugin tests

## GitHub Verification Snapshot

Observed final check results:

- `contracts` — success
- `plugin-tests` — success
- `regression` — success
- `perf-roadmap-9-3` — success
- `detect_changes (CI)` — success
- `detect_changes (regression)` — success

Regression runtime from GitHub:

- `regression` completed in `3m14s`

## Local Verification Basis

This PR stabilization conclusion is backed by the local remediation validation already executed in the previous slice:

- contracts slice: `9 passed`
- plugin slice: `31 passed, 1 skipped, 1 warning`
- ECO routing slice: `18 passed, 1 warning`
- Alembic smoke:
  - single main head after remediation
  - fresh-db `upgrade head` succeeded
- syntax check: passed

## Notes

- This document records the **final GitHub-side stabilization outcome**, not a new full local regression run.
- Full-repository regression was still not run in this slice.
- `Claude Code CLI` remained optional sidecar-only; the final check verification and PR operations were done locally.
