# Design: Document Sync Mirror Site Auth Contract

## Date

2026-04-07

## Scope

Add the minimum site-level auth contract needed before a mirror transport
adapter can exist:

- typed `auth_type`
- typed `auth_config`
- BasicAuth-compatible validation
- masked site serialization

This package does **not** add outbound HTTP transport, probe, or execution.

## Changes

| Area | Change |
|------|--------|
| `SyncSite` model | Added `auth_type` and `auth_config` |
| `DocumentSyncService.create_site()` | Added BasicAuth-compatible auth validation and normalization |
| `DocumentSyncService.update_site()` | Applies the same auth validation when auth fields change |
| `document_sync_router` | Accepts auth fields on site create and returns masked auth summary only |
| migration | Added schema columns on `meta_sync_sites` |

## Contract

### Supported auth types

- `basic`
- `none` / omitted

### `basic` requirements

`auth_config` must contain:

- `username`
- `password`

Both must be non-empty strings.

### Response masking

Site responses never return the raw password. For a BasicAuth-configured site,
the router returns:

```json
{
  "auth_type": "basic",
  "auth_config": {
    "username": "mirror-user",
    "has_password": true
  }
}
```

## Why This Package Comes Before Transport

The mirror transport adapter needs a stable and safe site contract to consume.
Without typed auth fields, any outbound adapter would be forced to guess field
names, masking semantics, and validation rules.

This package establishes that contract first and keeps the write set narrow.

## Non-Goals

This package does not:

- perform outbound HTTP requests
- add a probe endpoint
- add a mirror execution endpoint
- map remote results into `SyncJob` / `SyncRecord`
- introduce auth types beyond BasicAuth-compatible configuration

## Outcome

`document_sync` now has a safe mirror-site auth contract and masked API shape.
The next package can focus only on the outbound BasicAuth mirror adapter.
