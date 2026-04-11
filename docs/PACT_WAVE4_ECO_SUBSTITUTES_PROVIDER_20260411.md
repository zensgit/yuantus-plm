# Pact Wave 4 ECO And Substitutes Provider

## Scope

This provider slice makes Yuantus verify the next 5 Metasheet2 interactions:

- `GET /api/v1/eco`
- `GET /api/v1/eco/{id}`
- `GET /api/v1/bom/{bom_line_id}/substitutes`
- `POST /api/v1/bom/{bom_line_id}/substitutes`
- `DELETE /api/v1/bom/{bom_line_id}/substitutes/{substitute_id}`

The total pact count moves from 14 to 19 interactions.

## Design

1. Keep provider-state handling as a no-op.
The verifier still seeds once up front and does not mutate fixtures per state.

2. Reuse the existing fake user override.
No new auth harness was introduced. The same FastAPI dependency override keeps
protected BOM substitute routes deterministic.

3. Isolate substitute lifecycle fixtures by BOM line.
Wave 4 introduces:

- one BOM line with a seeded substitute for `GET`
- one BOM line with no substitute for `POST`
- one BOM line with a seeded substitute dedicated to `DELETE`

That avoids verification coupling to interaction order.

4. Reuse the existing ECO stage graph.
No separate ECO subsystem seed was added. `GET /eco` and `GET /eco/{id}` reuse
the Wave 3 ECO rows already needed by approvals.

## Files Changed

- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- `contracts/pacts/metasheet2-yuantus-plm.json`
- `docs/PACT_WAVE4_ECO_SUBSTITUTES_PROVIDER_20260411.md`

## Verification

Run from repo root:

```bash
./.venv/bin/python -m pytest src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q
```

Expected result for this wave:

- `1` test passed
- `19` pact interactions verified
