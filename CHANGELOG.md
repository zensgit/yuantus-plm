# Changelog

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
