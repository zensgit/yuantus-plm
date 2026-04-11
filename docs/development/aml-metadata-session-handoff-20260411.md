# AML Metadata Session Handoff

Date: 2026-04-11

## Purpose

This file is the continuation handoff for the AML metadata work across
Yuantus and Metasheet2.

It is meant to replace raw chat history with a repo-backed engineering note
that can be fetched on another machine through GitHub.

## What Was Decided

- Keep the integration contract-first.
- Treat Yuantus as the provider authority for AML metadata:
  - `GET /api/v1/aml/metadata/{type}`
- Treat Metasheet2 as the federation + UI consumer:
  - federation route exposes metadata to the web app
  - product panel renders AML metadata below the static field catalog
- Persist context in markdown docs rather than relying on chat state.

## Repos, Branches, PRs

### Yuantus

Working branch:

- `feature/claude-c43-cutted-parts-throughput`

Recent doc commits on this branch:

- `d24b5a4` `docs(pact): add aml metadata verification note`
- `6738eac` `docs(aml): add metadata federation and index`

Clean doc-only PR:

- `zensgit/yuantus-plm#197`
- https://github.com/zensgit/yuantus-plm/pull/197

### Metasheet2

AML metadata consumer/UI PR:

- `zensgit/metasheet2#825`
- https://github.com/zensgit/metasheet2/pull/825

Important fix commit there:

- `be3a1e6a` `fix(plm): preserve manual metadata hydration`

## Documents To Read First

### In Yuantus

- `docs/development/aml-metadata-pact-design-and-verification-20260411.md`
- `docs/development/aml-metadata-federation-design-verification-20260411.md`
- `docs/development/aml-metadata-doc-index-20260411.md`
- `docs/development/aml-metadata-session-handoff-20260411.md`

### In Metasheet2

- `docs/development/plm-product-metadata-panel-design-verification-20260411.md`

## Provider / Federation / Consumer Chain

The working path is:

`plmService.getMetadata(itemType)`
-> `plmFederationClient.getMetadata(itemType)`
-> `GET /api/federation/plm/metadata/:itemType`
-> `PLMAdapter.getItemMetadata(itemType)`
-> `GET /api/v1/aml/metadata/:itemType`

## What Was Implemented

### Yuantus Side

- provider-side Pact verification for AML metadata was documented
- pact sync / verifier run mode was documented
- federation design/verification note was written
- AML metadata doc index was added

### Metasheet2 Side

- AML metadata is rendered in the PLM product panel
- manual `/plm` load flow bug was fixed:
  - before the fix, clicking `加载产品` could fetch successfully but leave the
    DOM at `暂无产品详情`
  - cause: route sync wrote `productId` without `autoload=true`
  - hydration then cleared `product` after a successful `200`
  - fix: manual product route sync now carries `autoload=true` whenever product
    context should hydrate

## Verification Status

### Provider Pact

Recorded result:

- Yuantus provider verifier: `1 passed`

### Federation / Consumer Tests

Recorded result:

- consumer/federation test pack: `74 passed`

### Product Panel UI

Recorded result:

- `plmWorkbenchViewState.spec.ts`: `44 passed`
- metadata/UI test pack: `16 passed`

### Browser Smoke

Manual path verified:

1. open `/plm`
2. fill product ID `01H000000000000000000000P1`
3. keep item type `Part`
4. click `加载产品`

Expected good state:

- URL includes:
  - `productId=01H000000000000000000000P1`
  - `itemType=Part`
  - `autoload=true`
- DOM includes:
  - `Mounting Bracket`
  - `P-0001`
  - `Released`
  - `模型字段（AML Metadata，6）`

## How To Resume On Another Computer

### Yuantus

```bash
git clone <repo-url>
cd Yuantus
git fetch origin
git checkout feature/claude-c43-cutted-parts-throughput
```

Open:

- `docs/development/aml-metadata-session-handoff-20260411.md`
- `docs/development/aml-metadata-doc-index-20260411.md`

### Metasheet2

```bash
git clone <repo-url>
cd metasheet2
git fetch origin
git checkout <branch containing PR #825 work>
```

Or inspect directly on GitHub:

- `zensgit/metasheet2#825`
- `zensgit/yuantus-plm#197`

## Recommended Next Step

If work resumes, start from:

1. Yuantus doc-only PR `#197` for provider/federation context
2. Metasheet2 PR `#825` for consumer/UI context
3. this handoff file for the combined session state

## Notes

- GitHub will sync this handoff because it is just a committed markdown file.
- This is not the raw verbatim chat transcript; it is the durable engineering
  summary needed to continue work safely on another machine.
