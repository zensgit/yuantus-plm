# AML Metadata Pact Design and Verification

Date: `2026-04-11`

## Scope

This document records the provider-side Pact design for the AML metadata
surface in Yuantus and the exact verification workflow used to keep the
committed consumer pact in sync.

The focus is the real provider path used by the Metasheet2 consumer pact:

- `GET /api/v1/aml/metadata/{type}`

## 1. Provider-Side Pact Design

The provider verifier is intentionally lightweight:

- it starts the Yuantus FastAPI app in test mode
- it runs against an isolated SQLite database
- it pre-seeds a small, deterministic fixture set once before the server
  starts handling requests
- it verifies the committed Pact artifact rather than generating a new one

That design keeps the contract aligned to the wire boundary. The Pact checks
the provider response shape, while the application code continues to own the
actual AML metadata assembly logic.

The current pact copy lives at:

- `contracts/pacts/metasheet2-yuantus-plm.json`

The provider verifier entry point lives at:

- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`

## 2. Why `Property` Rows Must Be Seeded

The AML metadata endpoint does not infer its form/grid fields from `ItemType`
alone. The provider-side test seeds the minimal `Property` rows for the seeded
`Part` item type because the metadata endpoint reads `ItemType.properties` and
expects the underlying `Property` table to exist.

Without those rows, the provider can still boot, but the metadata response loses
the field definitions that the consumer contract is protecting. In practice,
that would make the Pact verification misleading: the route would exist, but the
discovered metadata shape would be incomplete or empty.

The seeded `Part` metadata set is intentionally small and stable:

- `item_number`
- `name`
- `description`
- `state`
- `cost`
- `weight`

That is enough to exercise the discovery contract without turning Pact into a
fixture-by-fixture business test.

## 3. `sync_metasheet2_pact.sh` Responsibilities

The sync helper is the operational bridge between the consumer repo and the
provider repo. It does three things:

1. reads the Metasheet2 source-of-truth pact from:
   `metasheet2/packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json`
2. compares it with the committed Yuantus copy at:
   `contracts/pacts/metasheet2-yuantus-plm.json`
3. optionally runs the local provider verifier after sync or drift check

Behavior by mode:

- `--check` fails when the two pact files differ and never writes files
- default mode copies the consumer pact into the Yuantus provider repo when
  drift exists
- `--verify-provider` runs the provider verifier after the check/sync step

The helper does not author the consumer pact and does not invent a second
provider-verifier path. It only mirrors the committed consumer artifact into the
provider repo.

## 4. Provider Verifier Run Mode

Use the Yuantus virtualenv Python explicitly and point `PYTHONPATH` at a clean
clone checkout of the repository before running pytest.

Example:

```bash
PYTHONPATH=/path/to/clean-clone/src \
  /Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

If you want to exercise the sync helper and verifier together:

```bash
METASHEET2_ROOT=/path/to/metasheet2 \
PYTHONPATH=/path/to/clean-clone/src \
  bash scripts/sync_metasheet2_pact.sh --verify-provider
```

The important part is that the verifier must import the provider code from the
clean clone through `PYTHONPATH`, while execution uses the repo-local
`.venv/bin/python` at:

- `/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python`

## 5. Verification Run and Result

Sync drift check:

```bash
METASHEET2_ROOT=/tmp/metasheet2-aml-metadata-6veqFJ \
  bash scripts/sync_metasheet2_pact.sh --check
```

Result:

```text
pact_sync=ok source_hash=82374b3a8151295c7f419f288eafad382955baa81f6b433eb3874712a8392c85 target_hash=82374b3a8151295c7f419f288eafad382955baa81f6b433eb3874712a8392c85
```

Provider verifier command:

```bash
METASHEET2_ROOT=/tmp/metasheet2-aml-metadata-6veqFJ \
PYTHONPATH=/tmp/yuantus-aml-metadata-sQmruU/src \
  /Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  -k provider_verifies_local_pacts
```

Result:

```text
provider_verifier=pass
result=1 passed, 3 warnings
duration=13.63s
```

## 6. Known Limits

- The provider verifier uses a single isolated SQLite database and global
  pre-seeding rather than per-provider-state data builders.
- The provider state handler is intentionally a no-op for now; state names exist
  for documentation and future expansion.
- The pact artifact is committed JSON, so the verification surface is stable but
  not auto-generated.
- Matching is intentionally shape-oriented, not value-oriented; exact IDs and
  timestamps are not the contract target.
- The helper script compares and copies a single pact artifact; it does not
  reconcile broader consumer-repo contract history.

## 7. Quick References

- `contracts/pacts/metasheet2-yuantus-plm.json`
- `scripts/sync_metasheet2_pact.sh`
- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- `docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md`
- `docs/PACT_WAVE2_DOCUMENT_SEMANTICS_PROVIDER_20260411.md`
