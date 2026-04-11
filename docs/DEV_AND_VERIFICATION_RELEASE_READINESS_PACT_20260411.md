# Release Readiness Pact Coverage

Date: 2026-04-11

## Scope

This slice closes the remaining gap between:

- real `metasheet2` consumer behavior
- the shared Metasheet <-> Yuantus Pact artifact

`release_readiness` was already implemented in `metasheet2` mainline:

- `PLMAdapter.getReleaseReadiness(...)`
- `POST /api/federation/plm/query` with `operation: "release_readiness"`
- unit contract coverage in `tests/unit/federation.contract.test.ts`

What was still missing was the shared Pact / provider-verifier protection for
the underlying Yuantus wire call:

- `GET /api/v1/release-readiness/items/{item_id}`

This change adds that endpoint to the canonical consumer pact and the Yuantus
provider verifier surface.

## Design

### 1. No new runtime architecture

No new service, adapter mode, or endpoint was introduced.

The design decision was to protect the **existing** mainline consumer call,
not invent another abstraction layer:

- consumer runtime stays in `metasheet2`
- provider runtime stays in `Yuantus`
- shared artifact stays the hand-authored Pact JSON

### 2. Pact locks the Yuantus wire envelope, not the adapter-mapped shape

The Pact interaction covers the raw provider response from:

- `GET /api/v1/release-readiness/items/01H000000000000000000000P1`

with query parameters:

- `ruleset_id=gate-a`
- `mbom_limit=10`
- `routing_limit=12`
- `baseline_limit=8`

Important boundary:

- Pact response shape is the **Yuantus API response**
- adapter-added `links.summary` / `links.export` remain a `metasheet2`
  mapping concern and are already covered by unit tests

This keeps the contract aligned to the actual network boundary.

### 3. Provider seed stayed minimal

No extra release-readiness fixture graph was required.

The existing provider verifier already seeds:

- admin user
- primary `Part` item `01H000000000000000000000P1`

`ReleaseReadinessService` returns a valid empty readiness summary when there
are no MBOM / routing / baseline resources for that item, so the new Pact
interaction could be verified without expanding the provider state handler.

## Files Changed

### metasheet2

- `packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json`
- `packages/core-backend/tests/contract/plm-adapter-yuantus.pact.test.ts`
- `packages/core-backend/tests/contract/README.md`

### Yuantus

- `contracts/pacts/metasheet2-yuantus-plm.json`
- `docs/DEV_AND_VERIFICATION_METASHEET_YUANTUS_PACT_CLOSURE_20260411.md`
- `docs/DEV_AND_VERIFICATION_RELEASE_READINESS_PACT_20260411.md`

## Verification

### Consumer pact sanity

```bash
cd /tmp/metasheet2-pact-final-*/packages/core-backend
pnpm test:contract
```

Observed result:

- `2` files passed
- `17` tests passed

### Provider verifier

```bash
cd /tmp/yuantus-pact-main-*
/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m pytest \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q
```

Observed result:

- `1 passed`

### Provider + CI gate batch

```bash
cd /tmp/yuantus-pact-main-*
/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m pytest \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py -q
```

Observed result:

- `3 passed`

### Additional consumer coverage note

`metasheet2` already had runtime coverage for this slice before the Pact
change:

- `tests/unit/plm-adapter-yuantus.test.ts`
- `tests/unit/federation.contract.test.ts`

The Pact addition closes the gap between those existing runtime tests and the
shared cross-repo compatibility gate.

## End State

After this slice:

- release readiness is no longer a live-but-unprotected federation surface
- the protected contract surface moves from `28` to `29` interactions
- the Pact artifact now matches the real `metasheet2` governance call set on
  mainline

This is the correct stopping point for this slice. The next contract additions
should only happen when a new real consumer call lands.
