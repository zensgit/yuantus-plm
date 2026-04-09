# Pact Artifacts

This directory is reserved for committed Pact consumer artifacts used to verify
external integrations against Yuantus as the provider.

Current intended use:

- Metasheet2 consumer pact files targeting Yuantus PLM APIs

Recommended artifact naming:

- `metasheet2-yuantus-plm.json`

Provider verification entry point:

- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`

Notes:

- Keep pact files human-reviewable and committed to the repo.
- Prefer stable file names so CI and local verification commands stay simple.
- Additive fields are usually acceptable; destructive schema changes should go
  through contract review.
