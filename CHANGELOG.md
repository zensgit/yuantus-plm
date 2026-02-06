# Changelog

## v0.1.4 (Update) - 2026-02-03

### Added
- Baseline effective-date lookup endpoint for released baselines.
- E-sign signing reason update/deactivate support and meaning filter.
- Advanced search filter operators: startswith, endswith, not_contains.
- Manufacturing WorkCenter API skeleton (list/get/create/update) with service layer and automated tests.
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
