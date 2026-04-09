# C12 - Approvals Durable Audit Surpass Design (2026-03-23)

## 1. Goal

Upgrade approvals from a synthetic-read layer to a durable audit layer while keeping the read contracts backward compatible.

This phase adds:
- a persistent `ApprovalRequestEvent` audit table
- lifecycle and history reads backed by stored events
- fallback rendering from legacy request columns when event rows are absent
- migration alignment for approvals and subcontracting tables under `SCHEMA_MODE=migrations`
- bootstrap alignment so `create_all()` registers the new models
- case-insensitive export format normalization

## 2. API / Read Model Changes

### Request history and lifecycle

History and lifecycle endpoints now prefer persisted events:
- `ApprovalRequestEvent` rows are the primary source for audit history
- legacy rows without events continue to render from request timestamps and state columns
- resubmission history is preserved as a separate event trail

### Export normalization

Approvals export endpoints normalize `format` with `strip().lower()`, so callers can send values like `JSON`, `Csv`, or `markdown` without contract drift.

## 3. Schema Alignment

### Durable audit table

`meta_approval_request_events` stores the request audit trail with:
- request linkage
- event type
- transition type
- from/to state
- actor and note fields
- extensible JSON properties
- generated timestamps

### Migration alignment

The migration layer now aligns approvals and subcontracting tables with the runtime models so deployments using `SCHEMA_MODE=migrations` can create the same domain surface as `create_all()`.

### Bootstrap alignment

`bootstrap.import_all_models()` imports approvals and subcontracting models explicitly, ensuring the new tables are registered before metadata creation.

## 4. Compatibility Notes

- No existing read endpoints were removed.
- Legacy approvals rows remain readable even if no event rows exist yet.
- The new event table is additive and can be populated incrementally.
- The durable audit trail is the preferred source for future history reads.

## 5. Files

- `src/yuantus/meta_engine/approvals/models.py`
- `src/yuantus/meta_engine/approvals/service.py`
- `src/yuantus/meta_engine/web/approvals_router.py`
- `src/yuantus/meta_engine/bootstrap.py`
- `migrations/versions/a2b2c3d4e7a6_add_approvals_and_subcontracting_tables.py`
