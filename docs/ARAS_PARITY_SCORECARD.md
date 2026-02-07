# Aras Parity Scorecard

## 1. Metrics Definition

This scorecard tracks parity-to-surpass progress against roadmap scope.

| Metric | Definition |
|---|---|
| Capability coverage rate | Delivered roadmap capabilities / planned capabilities |
| Quality pass rate | Green runs / required runs under strict gates |
| Performance attainment rate | Met performance targets / total performance targets |
| Leading capability count | Number of capabilities measurably ahead of Aras baseline in target scenarios |

## 2. Current Snapshot (2026-02-07)

| Metric | Current |
|---|---|
| Capability coverage rate | 6 / 6 phases with implemented core capability (`100%`) |
| Quality pass rate | `100%` (latest strict gate report PASS: `docs/DAILY_REPORTS/STRICT_GATE_20260207-220207.md`; CI green on merged PRs) |
| Performance attainment rate | 6 / 6 targets met (see `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260207-135822.md`) |
| Leading capability count | 4 (strict regression evidence autopack, cross-domain impact + release readiness summary APIs + export bundles, strategy-based validation rulesets + diagnostics for manufacturing + baselines + ECO apply + ruleset directory, item cockpit cross-domain cockpit API + export bundle) |

## 3. Notes

- Capability coverage is phase-level and intentionally conservative.
- Performance metrics must be updated after weekly benchmark run against roadmap section 9.3.
- Leading capability count requires scenario evidence and reproducible verification records.
- Product detail now supports cockpit flags to surface cross-domain links/summaries in one call (UI integration without extra round-trips).
