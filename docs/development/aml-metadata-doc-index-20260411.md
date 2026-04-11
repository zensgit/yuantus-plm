# AML Metadata Doc Index

Date: 2026-04-11

## Purpose

This index ties together the three documents that define and verify the
`aml/metadata` integration across Yuantus and Metasheet2.

Use it as the single entry point when reviewing:

- provider-side Pact verification
- federation bridge design
- consumer-side UI behavior and browser validation

## Document Map

### 1. Provider Pact Verification

File:

- `docs/development/aml-metadata-pact-design-and-verification-20260411.md`

Focus:

- Yuantus provider verifier design
- fixture seeding requirements
- pact sync script behavior
- provider verification commands and results

### 2. Federation Bridge Design

File:

- `docs/development/aml-metadata-federation-design-verification-20260411.md`

Focus:

- end-to-end request path from Metasheet service to Yuantus AML
- canonical metadata contract shape
- federation route and adapter responsibilities
- consumer/federation contract verification result

### 3. Consumer UI Integration

Sibling repo:

- `../../../metasheet2/docs/development/plm-product-metadata-panel-design-verification-20260411.md`

Focus:

- product panel AML metadata rendering
- manual load route-hydration bug and fix
- browser smoke proving `Mounting Bracket` and `模型字段（AML Metadata，6）`

## Recommended Reading Order

1. Provider Pact verification
2. Federation bridge design
3. Consumer UI integration

That order matches the dependency chain:

`Yuantus provider -> federation bridge -> Metasheet UI`

## Quick Status

- provider pact verification: green
- federation metadata route contract: green
- manual `/plm` product load path: green after route-hydration fix

## Related Paths

- `contracts/pacts/metasheet2-yuantus-plm.json`
- `scripts/sync_metasheet2_pact.sh`
- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- `docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md`
