# Pact Wave 5 CAD Provider

## Scope

This provider slice extends Yuantus verification for the 9 CAD interactions
added in Wave 5:

- `GET /api/v1/cad/files/{file_id}/properties`
- `PATCH /api/v1/cad/files/{file_id}/properties`
- `GET /api/v1/cad/files/{file_id}/view-state`
- `PATCH /api/v1/cad/files/{file_id}/view-state`
- `GET /api/v1/cad/files/{file_id}/review`
- `POST /api/v1/cad/files/{file_id}/review`
- `GET /api/v1/cad/files/{file_id}/history`
- `GET /api/v1/cad/files/{file_id}/diff`
- `GET /api/v1/cad/files/{file_id}/mesh-stats`

The total pact count moves from 19 to 28 interactions.

## Fixture IDs

The Wave 5 verifier seeds these exact file IDs:

- `01H000000000000000000000F2`
- `01H000000000000000000000F3`
- `01H000000000000000000000F4`
- `01H000000000000000000000F5`
- `01H000000000000000000000F6`
- `01H000000000000000000000F7`
- `01H000000000000000000000F8`
- `01H000000000000000000000F9`
- `01H000000000000000000000F10`
- `01H000000000000000000000F11`

## Design

1. Keep the existing verifier harness.
Wave 5 extends `test_pact_provider_yuantus_plm.py`; it does not introduce a
second provider runner or a second state-handler path.

2. Keep provider-state handling as a no-op.
Each mutating CAD route uses a dedicated file fixture:

- CAD properties read and write use different files
- CAD view-state read and write use different files
- CAD review read and write use different files

That avoids verification-order coupling without per-state DB mutation.

3. Seed history and diff explicitly.
Wave 5 adds dedicated `CadChangeLog` rows for the history interaction and a
dedicated left/right CAD file pair for the diff interaction.

4. Patch storage reads only where required.
`PATCH /view-state` needs a CAD document payload for entity-id validation and
`GET /mesh-stats` needs a CAD metadata payload. The verifier patches
`FileService.download_file` inside the provider runtime so those paths resolve
from in-memory JSON fixtures instead of external storage.

## Files Changed

- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- `docs/PACT_WAVE5_CAD_PROVIDER_20260411.md`

## Verification

Run from repo root:

```bash
./.venv/bin/python -m pytest src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q
```

Expected result for this wave:

- `1` test passed
- `28` pact interactions verified
