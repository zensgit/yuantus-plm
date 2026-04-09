# Pact-First Integration Plan

## Objective

Protect the already-running Metasheet-to-Yuantus federation path before adding more product surface.

The working model is:

- shared contract
- separate implementations
- CI-enforced compatibility

Without Pact verification, "independent evolution" is only an assumption.

## Why This Comes First

Metasheet already talks to Yuantus through `PLMAdapter` in `yuantus` mode. The integration is live at the adapter level, so the first engineering priority is to freeze the contract shape before either repo evolves further.

Relevant current client:

- `/Users/huazhou/Downloads/Github/metasheet2/packages/core-backend/src/data-adapters/PLMAdapter.ts`

Relevant current server routes:

- [router.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/router.py)
- [query_router.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/query_router.py)
- [search_router.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/search_router.py)
- [bom_router.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/bom_router.py)
- [eco_router.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/eco_router.py)
- [file_router.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/file_router.py)

## Wave 1 Contract Set

These are the first contracts to lock because the adapter is already using them today.

| Priority | Consumer Endpoint | Current Use |
| --- | --- | --- |
| `P0` | `POST /api/v1/auth/login` | credential-based token fetch |
| `P0` | `GET /api/v1/health` | connectivity and health probing |
| `P0` | `GET /api/v1/search/` | product list and search |
| `P0` | `POST /api/v1/aml/apply` | product detail lookup |
| `P0` | `GET /api/v1/bom/{id}/tree` | BOM tree rendering |
| `P0` | `GET /api/v1/bom/compare` | BOM compare |
| `P1` | `GET /api/v1/bom/{id}/where-used` | reverse structure lookup |
| `P1` | `GET /api/v1/bom/compare/schema` | compare field metadata |
| `P1` | `GET /api/v1/file/item/{item_id}` | product document list |
| `P1` | `GET /api/v1/eco/{id}/approvals` | approval history |
| `P1` | `POST /api/v1/eco/{id}/approve` | approval action |
| `P1` | `POST /api/v1/eco/{id}/reject` | rejection action |

### Wave 1.5: Anticipated But Not Yet Adopted

These endpoints are strategically important, but should not be part of the first
consumer pact unless the current Metasheet mainline adapter actually calls them.

| Endpoint | Why It Matters | Current Status |
| --- | --- | --- |
| `GET /api/v1/aml/metadata/{item_type_name}` | schema/form metadata discovery for front-end rendering | present in Yuantus, but not yet called by current Metasheet mainline adapter |
| `POST /api/v1/aml/query` | generic AML list/query flows | add when Metasheet begins depending on generic AML querying directly |

The contract rule is consumer-driven: if the mainline consumer does not call the
endpoint yet, do not pretend it is protected by Wave 1.

## Recommended Artifact Locations

### Metasheet Consumer Side

Suggested files:

- `packages/core-backend/tests/contract/plm-adapter-yuantus.pact.test.ts`
- `packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json`

### Yuantus Provider Side

Suggested files:

- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- optional shared pact copy under `contracts/pacts/`

Current status:

- provider verification skeleton already exists at
  [test_pact_provider_yuantus_plm.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/api/tests/test_pact_provider_yuantus_plm.py)
- pact artifact directory convention already exists at
  [contracts/pacts/README.md](/Users/huazhou/Downloads/Github/Yuantus/contracts/pacts/README.md)

So the next step is to extend the existing skeleton, not create a second provider verifier path.

The exact file paths can be adjusted later, but the pact artifact should be stored in a stable, reviewable location rather than as an opaque CI temp file.

## Match Strategy

Use schema-shape matching, not exact value matching.

Prefer:

- `Matchers.string()`
- `Matchers.integer()`
- `Matchers.like(...)`
- optional-field tolerant matching

Avoid:

- exact timestamps
- exact IDs
- exact result counts unless count semantics are part of the contract

The goal is to freeze response shape and required semantics, not test business fixtures through Pact.

## Two-Week Execution Sequence

### Week 1: Build the Safety Net

#### Day 1-2

Implement consumer Pact tests in Metasheet for:

- `POST /api/v1/auth/login`
- `GET /api/v1/health`
- `GET /api/v1/search/`
- `POST /api/v1/aml/apply`
- `GET /api/v1/bom/{id}/tree`
- `GET /api/v1/bom/compare`

#### Day 3-4

Implement provider verification in Yuantus:

- start the FastAPI app in test mode
- load the generated pact
- verify provider responses against the pact
- wire the verifier into regular CI

#### Day 5

Run one deliberate break experiment:

- temporarily rename a pact-protected field in a branch-only change
- confirm consumer/provider CI fails
- revert the break and merge only the pact infrastructure

This is required proof that the pact gate is real.

### Week 2: Expand Coverage and Make It Operational

#### Day 6-7

Add second-wave contracts for:

- `GET /api/v1/bom/{id}/where-used`
- `GET /api/v1/bom/compare/schema`
- `GET /api/v1/file/item/{item_id}`
- `GET /api/v1/eco/{id}/approvals`
- `POST /api/v1/eco/{id}/approve`
- `POST /api/v1/eco/{id}/reject`

#### Day 8-10

Wire contract verification into developer workflow:

- CI gate on both repos
- visible pact artifact location
- documented local run command
- PR template note for public contract changes

## Done Criteria

The pact-first milestone is complete when:

1. Metasheet consumer pact tests generate a committed pact artifact.
2. Yuantus provider verification runs in CI.
3. A deliberate break experiment proves CI goes red.
4. New public PLM endpoint changes are treated as contract changes, not casual refactors.
5. Wave 1 protects only real mainline consumer calls; anticipated endpoints stay outside the pact until adopted.

## Anti-Goals

This plan is not trying to:

- replace integration tests
- fully model every endpoint at once
- freeze payload values
- block all additive changes

It is specifically trying to stop silent breakage across repos.

## Source-Of-Truth Decision For Consumer Pact

There is an open repo-boundary question between:

- `metasheet2`
- `metasheet2-plm-workbench`

The consumer pact should be authored in only one source-of-truth repo.

Current recommendation:

- prefer `metasheet2` mainline as the long-term consumer contract source
- treat `metasheet2-plm-workbench` as a spike or staging branch unless deployment reality proves otherwise

This decision should be verified before implementing duplicate pact suites in both repos.

## Next Step After Pact

Once Wave 1 and Wave 2 are green, the next safe expansion is:

- `PLM Workspace` front-end evolution in Yuantus
- `saved views` and bounded collaboration features in Yuantus
- richer Metasheet front-end experiences over the same protected contracts

## Related Strategy Docs

- [PLM_STANDALONE_METASHEET_BOUNDARY_STRATEGY_20260407.md](/Users/huazhou/Downloads/Github/Yuantus/docs/PLM_STANDALONE_METASHEET_BOUNDARY_STRATEGY_20260407.md)
- [PRODUCT_SKU_MATRIX.md](/Users/huazhou/Downloads/Github/Yuantus/docs/PRODUCT_SKU_MATRIX.md)
- [WORKFLOW_OWNERSHIP_RULES.md](/Users/huazhou/Downloads/Github/Yuantus/docs/WORKFLOW_OWNERSHIP_RULES.md)
