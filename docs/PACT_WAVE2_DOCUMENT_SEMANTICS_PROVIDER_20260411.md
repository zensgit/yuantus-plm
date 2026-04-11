# Pact Wave 2 Document Semantics Provider

## Goal

Verify Yuantus as the provider for the document semantics interactions already
used by Metasheet2:

- `GET /api/v1/file/item/{item_id}`
- `GET /api/v1/file/{file_id}`
- `POST /api/v1/aml/query` with `expand: ['Document Part']`

This slice also fixed the canonical AML query route so the provider now serves
the path the real consumers already call: `/api/v1/aml/query`.

## Design

### Canonical AML query path

`query_router` now mounts under `/aml`, so with the existing app prefix the
public provider path is:

- `/api/v1/aml/query`

This aligns Yuantus with:

- Metasheet `PLMAdapter.ts`
- native `plm_workspace.html`
- native `workbench.html`

### Provider fixture expansion

The pact provider verifier still uses a single isolated SQLite database and
global pre-seeding. This slice extends the seed set with:

- `ItemType('Document')`
- `ItemType('Document Part')`
- one related `Document` item
- one `Document Part` relationship from the seeded `Part`
- one `FileContainer`
- one `ItemFile`

That makes the provider capable of satisfying all 9 pact interactions from the
same verifier harness without adding a second verifier.

### Compatibility note

The provider seed adds relationship properties to the `Document Part` fixture so
the current BOM tree walker contract remains satisfied when the seeded Part owns
both BOM and document relations in the same isolated database.

## Files Changed

- `src/yuantus/meta_engine/web/query_router.py`
- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- `contracts/pacts/metasheet2-yuantus-plm.json`

## Verification

Command:

```bash
cd /tmp/yuantus-docs-wave2-VE5QGH
./.venv/bin/python -m pytest src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q
```

Result:

```text
1 passed
```

Observed verifier outcome:

- all 9 interactions matched
- canonical `/api/v1/aml/query` returned `200`
- document semantics no longer degrade to a route-level `404`
