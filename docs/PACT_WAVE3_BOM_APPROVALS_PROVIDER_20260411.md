# Pact Wave 3 BOM And Approvals Provider

## Scope

This provider slice makes Yuantus verify the 5 new consumer interactions added
in Metasheet2 Wave 3:

- `GET /api/v1/bom/{id}/where-used`
- `GET /api/v1/bom/compare/schema`
- `GET /api/v1/eco/{id}/approvals`
- `POST /api/v1/eco/{id}/approve`
- `POST /api/v1/eco/{id}/reject`

The full pact count moves from 9 to 14 interactions.

## Design

1. Keep the provider state handler as a no-op.
The verifier continues to pre-seed everything once at startup instead of
mutating state per interaction.

2. Avoid mutation cross-talk by using distinct ECO fixtures.
Wave 3 introduces three separate ECO IDs:

- history ECO
- approve ECO
- reject ECO

`approve` and `reject` are therefore free to mutate their own rows without
changing the expectations for `history`.

3. Seed the minimum approval graph, not the full workflow stack.
The verifier now seeds:

- one `RBACUser(id=1)` approval actor
- three `ECOStage` rows
- three `ECO` rows
- one pending `ECOApproval` history row

This is enough to satisfy the contract without inventing broader fixture
machinery.

4. Force stable approval identity for action routes.
`get_current_user_id_optional` is overridden to return the same fake user id as
the existing auth bypass. That keeps `approve` / `reject` deterministic.

## Files Changed

- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- `contracts/pacts/metasheet2-yuantus-plm.json`

## Verification

Run from repo root:

```bash
./.venv/bin/python -m pytest src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q
```

Observed result on 2026-04-11:

- `1 passed, 3 warnings`

Warnings are existing dependency deprecations from `pact-python` / `websockets`
and do not indicate contract drift.
