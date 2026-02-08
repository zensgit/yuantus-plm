# Changelog

## v0.1.4 (Update) - 2026-02-08

### Added
- Release orchestration API (admin-only):
  - `GET /api/v1/release-orchestration/items/{item_id}/plan`
  - `POST /api/v1/release-orchestration/items/{item_id}/execute` (routing -> mbom -> baseline; baseline optional)
- Playwright regression: release orchestration rollback when baseline is blocked by incomplete e-sign.
- Playwright regression: release orchestration rollback on injected routing-release failure (test-only failpoint).
- Playwright regression: reports summary endpoint (`GET /api/v1/reports/summary`).
- P5 reports/search performance harness:
  - `scripts/perf_p5_reports.py` + reports in `docs/PERFORMANCE_REPORTS/`
  - Baseline gate: `scripts/perf_p5_reports_gate.py` (compare current run vs recent CI artifacts)
  - CI schedule: `.github/workflows/perf-p5-reports.yml`
- Perf CI: `perf-p5-reports` also runs on pull requests via paths filter (smaller seed sizes).
- Reports summary: add `windows.last_24h` and `windows.last_7d` time-window counts.
- Dev doc: test-only failpoints (`docs/DEV_FAILPOINTS.md`).

### Changed
- Release orchestration execute: validate `ruleset_id` up-front, support `rollback_on_failure` (best-effort reopen to draft), and honor `baseline_force` for diagnostics errors (baseline-only; still blocked by e-sign gate).
- Release orchestration execute: stabilize execution ordering (resource_id asc) to align with plan steps.
- Demo closed-loop script: supports `DEMO_USE_RELEASE_ORCHESTRATION=1` to release via orchestration (plan + execute).
- Reports summary: expand breakdown dimensions (manufacturing + file conversion/native/connector summaries).
- P5 reports/search perf harness: add reports summary + saved search run scenarios; trend now includes DB label; CI runs both SQLite and Postgres and gates against recent CI baselines.

### Verification
- Results logged in `docs/VERIFICATION_RESULTS.md`.

## v0.1.4 (Update) - 2026-02-07

### Added
- Strict gate scripts: `scripts/strict_gate.sh` (runner) and `scripts/strict_gate_report.sh` (report + logs) for unattended regression evidence.
- CI strict gate workflow: `.github/workflows/strict-gate.yml` (scheduled + manual dispatch; uploads strict gate report + logs as artifacts).
- Demo closed-loop script: `scripts/demo_plm_closed_loop.sh` (EBOM -> Baseline -> MBOM -> Routing -> release/readiness/cockpit exports) and optional strict gate integration via `DEMO_SCRIPT=1`.
- Impact summary API: `GET /api/v1/impact/items/{item_id}/summary` (BOM where-used + baselines + e-sign summary).
- Impact summary export bundle: `GET /api/v1/impact/items/{item_id}/summary/export?export_format=zip|json` (zip includes JSON + CSV tables).
- Item cockpit API: `GET /api/v1/items/{item_id}/cockpit` (aggregates impact summary + release readiness + open ECO hits + export links).
- Item cockpit export bundle: `GET /api/v1/items/{item_id}/cockpit/export?export_format=zip|json` (zip includes JSON + CSV tables).
- Product detail cockpit flags: `GET /api/v1/products/{item_id}` supports optional cockpit expansions (`include_impact_summary`, `include_release_readiness_summary`, `include_open_eco_hits`) and returns `cockpit_links` + `{authorized:...}` summaries (links-only by default via `cockpit_links_only=true`).
- Playwright API-only regression: `playwright/tests/export_bundles_api.spec.js` validates baseline release-diagnostics + export bundle endpoints (ZIP signature + attachment filenames).
- Strategy-based release validation (manufacturing): structured diagnostics APIs and configurable rulesets via `YUANTUS_RELEASE_VALIDATION_RULESETS_JSON`.
  - `GET /api/v1/routings/{routing_id}/release-diagnostics`
  - `GET /api/v1/mboms/{mbom_id}/release-diagnostics`
- Strategy-based release validation (baselines): structured diagnostics for baseline release.
  - `GET /api/v1/baselines/{baseline_id}/release-diagnostics`
- Release validation directory: `GET /api/v1/release-validation/rulesets` (list kinds/rulesets/rules; built-in + configured).
- ECO apply diagnostics: `GET /api/v1/eco/{eco_id}/apply-diagnostics` (strategy-based precheck, side-effect free).
- Release readiness summary: `GET /api/v1/release-readiness/items/{item_id}` (aggregates MBOM/Routing/Baseline diagnostics + E-sign manifest status).
- Release readiness export bundle: `GET /api/v1/release-readiness/items/{item_id}/export?export_format=zip|json` (zip includes JSON + CSV tables).
- Roadmap 9.3 performance benchmark harness: `scripts/perf_roadmap_9_3.py` + reports in `docs/PERFORMANCE_REPORTS/`.

### Changed
- Performance: Roadmap 9.3 harness now measures end-to-end dedup batch processing (1000 files) via a Dedup Vision sidecar when available (no longer SKIP).
- Baselines: enforce permission checks for compare/validate/release and comparison details/export; stabilize baseline member pagination order.
- E-sign: accept rotated HMAC secrets for verification (via `YUANTUS_ESIGN_VERIFY_SECRET_KEYS`), log verifier identity in audit, and restrict audit endpoints to admin.
- Search: add unit coverage for DB fallback behavior when Elasticsearch is unavailable.
- Manufacturing: routing/MBOM release endpoints accept optional `ruleset_id` query param (default behavior unchanged).
- Baselines: release endpoint accepts optional `ruleset_id` query param and blocks release on diagnostics errors unless `force=true`.
- Release validation: add built-in `readiness` ruleset for `routing_release`/`mbom_release`/`baseline_release` (excludes `*.not_already_released`).
- ECO: apply endpoint accepts `ruleset_id`, `force`, `ignore_conflicts` and blocks apply on diagnostics errors unless forced.

### Verification
- Results logged in `docs/VERIFICATION_RESULTS.md`.

## v0.1.4 (Update) - 2026-02-03

### Added
- Baseline effective-date lookup endpoint for released baselines.
- E-sign signing reason update/deactivate support and meaning filter.
- Advanced search filter operators: startswith, endswith, not_contains.
- Manufacturing WorkCenter API skeleton (list/get/create/update) with service layer and automated tests.
- Manufacturing guardrails: operation workcenter validation + admin-only WorkCenter writes.
- Manufacturing routing operations now support strong `workcenter_id` association with backward-compatible `workcenter_code` validation and id/code consistency enforcement.
- Manufacturing routing now supports scoped primary control (`PUT /routings/{id}/primary`) and filtered routing listing (`GET /routings?item_id|mbom_id`).
- Manufacturing lifecycle closure: operation update/delete/resequence APIs, routing/MBOM release-reopen flow, write-permission consolidation, and plant/line consistency checks.
- API examples updated for baseline effective date, e-sign reason update, and new search ops.
- Unit tests for baseline effective lookup, signing reason updates, and search filters.

### Verification
- Results logged in `docs/VERIFICATION_RESULTS.md`.

## v0.1.3 (Update) - 2026-02-01

### Added
- Config variants: option validation, variant rules, effective BOM, configuration instances.
- Manufacturing MBOM + routing: EBOM -> MBOM, MBOM lines, routing/operations, time & cost estimates.
- Baseline enhancements: members/comparisons, validation/release workflow, and extended baseline metadata.
- Advanced search & reporting: saved searches, report definitions/executions, dashboards.
- Electronic signatures: signing reasons, signature records, manifests, and audit logs.
- Report exports: CSV/JSON export and execution history endpoints.
- Baseline comparison export + details pagination.
- E-sign audit summary + audit export endpoints.
- Verification: scripts for config variants and MBOM/routing, plus new unit tests.

### Verification
- Results logged in `docs/VERIFICATION_RESULTS.md`.

### Tests
- Added pytest guardrails (testpaths + norecursedirs + DB opt-in) and stabilized DB-enabled runs.

## v0.1.3 - 2026-01-29

### Added
- Config variant conditions: extended operators (eq/ne/gt/gte/lt/lte/in/contains/regex/exists/missing/range).
- Product detail file aliases: name/type/role/mime/size/version/created_on/updated_on.
- Product detail summaries: document_summary.items, eco_summary.items.
- BOM UI aliases: parent/child number & name; substitute_number/substitute_name.
- UI integration checklist and verification docs.

### Verification
- Full regression (RUN_UI_AGG=1 + RUN_CONFIG_VARIANTS=1): PASS=43, FAIL=0, SKIP=10.

## v0.1.2 - 2026-01-28

### Added
- S12 Configuration/Variant BOM: option sets + options API.
- BOM config filtering via `config_condition` and `config` query param.
- Verification scripts and docs for config variants.

### Verification
- Full regression (RUN_CONFIG_VARIANTS=1): PASS=37, FAIL=0, SKIP=16.
