# TODO - Phase 4 P4.1.6 Search Indexer Lag Age Status

Date: 2026-05-06

## Scope

- [x] Preserve all existing P4.1 through P4.1.5 status fields.
- [x] Preserve existing `last_*_at` ISO timestamp fields.
- [x] Add internal datetime snapshots for received events.
- [x] Add internal datetime snapshots for success outcomes.
- [x] Add internal datetime snapshots for skipped outcomes.
- [x] Add internal datetime snapshots for error outcomes.
- [x] Add `last_event_age_seconds`.
- [x] Add `last_success_age_seconds`.
- [x] Add `last_skipped_age_seconds`.
- [x] Add `last_error_age_seconds`.
- [x] Emit non-null age fields as Prometheus gauges.
- [x] Omit null age fields from Prometheus output.
- [x] Cover success, skipped, and error age updates.
- [x] Update runbook and delivery-doc index.
- [x] Add taskbook and verification MD.

## Explicitly Not Done

- [ ] Add durable outbox-backed lag.
- [ ] Add background indexing worker lag.
- [ ] Add alert thresholds.
- [ ] Add cross-process aggregation.
- [ ] Add tenant/org/user/item/ECO labels.
- [ ] Change CAD material-sync plugin files.
