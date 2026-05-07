# TODO - Phase 4 Search Closeout

Date: 2026-05-07

## Checklist

- [x] Confirm P4.1 and P4.2 are merged on `origin/main`.
- [x] Add Phase 4 closeout contract tests.
- [x] Pin final Phase 4 public routes and route count.
- [x] Pin search-indexer status schema, event coverage, and metric surface.
- [x] Pin runtime runbook search-indexer and search-report documentation.
- [x] Clarify the runbook link between search-indexer metrics and
  `GET /api/v1/search/indexer/status`.
- [x] Add final Phase 4 development and verification MD.
- [x] Register the new contract in the CI `contracts` job.
- [x] Add all new MD files to `docs/DELIVERY_DOC_INDEX.md`.
- [ ] Merge P4.3 after CI is green.
- [ ] Do not start Phase 5 without explicit opt-in.

## Notes

This is a closeout-only slice. It intentionally does not implement
Elasticsearch aggregations, dashboards, UI, alert rules, or additional search
routes.
