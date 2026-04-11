# Metasheet <-> Yuantus Mainline Closeout

Date: 2026-04-11

## Scope

This document records the mainline closeout state after the current
Metasheet-to-Yuantus federation plan was fully landed across both repos.

At this point, the following tracks are on default branch:

- product boundary lock (`PLM Base` / `Collab Pack` / `Metasheet Platform` / `Combined`)
- shared-contract / separate-runtime pact model
- Wave 1 through Wave 5 provider and consumer contract coverage
- release-readiness federation coverage
- pact sync helper and provider CI gate hardening
- compose SKU profile overlays and smoke harness
- native workspace readiness drilldowns and ECO approval actions

This is a closeout verification slice, not a new architecture slice.

## Design Lock

### 1. Contract model

The cross-repo boundary stays:

- shared contract
- separate implementations
- CI-enforced compatibility

No shared Python/TypeScript runtime library was introduced.

### 2. Ownership model

- consumer pact source-of-truth stays in `metasheet2`
- provider verifier and committed pact copy stay in `Yuantus`
- `scripts/sync_metasheet2_pact.sh` is the operational bridge that checks or
  refreshes the provider-side pact copy from the consumer source

### 3. Deployment model

The packaging model is now concrete and mainline-backed:

- `base`: Yuantus-only PLM runtime
- `collab`: Yuantus runtime with collaboration gate enabled
- `combined`: Yuantus authoritative runtime + Metasheet sidecar runtime

This is expressed through compose overlays, not through duplicated services or
data migration.

### 4. Workspace / federation model

The current integrated surface now includes:

- product detail and search federation
- document semantics:
  - file attachments via `/api/v1/file/item/{item_id}`
  - AML related documents via `/api/v1/aml/query` with `expand: ["Document Part"]`
- BOM analysis and substitutes
- ECO approval detail and approve/reject actions
- release-readiness drilldowns
- native workspace readiness rails and ECO approval actions

## Mainline Revisions Verified

### Yuantus

- main HEAD: `b7bf61befb96620bbf9e57b8521566b4ebb21875`
- includes:
  - PR `#194` pact sync helper merge
  - PR `#193` compose smoke commands
  - PR `#192` compose delivery profiles
  - PR `#191` native ECO approval actions
  - PR `#190` release-readiness federation coverage
  - PR `#181` through `#188` pact wave/provider hardening sequence

### metasheet2

- main HEAD: `e1016dbca`
- already contains the current consumer pact, adapter mapping, and federation
  route coverage used by this integration track

## Verification

### 1. Pact sync check

Command:

```bash
cd /tmp/yuantus-mainline-closeout-*/
METASHEET2_ROOT=/tmp/metasheet2-pact-wave-sync-1k4fiv \
  bash scripts/sync_metasheet2_pact.sh --check
```

Observed result:

```text
pact_sync=ok source_hash=03df311fa986b809233553dccc0907457e1aa02cc733ca398d6114ae9401342b target_hash=03df311fa986b809233553dccc0907457e1aa02cc733ca398d6114ae9401342b
```

Conclusion:

- consumer pact source and provider pact copy are in sync on mainline

### 2. Provider verifier

Command:

```bash
cd /tmp/yuantus-mainline-closeout-*/
/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Observed result:

```text
1 passed, 3 warnings in 15.05s
```

Warnings were deprecation-only (`pact`, `websockets`, legacy relationship
import path) and did not affect the verifier outcome.

### 3. Consumer pact sanity on clean mainline worktree

Command:

```bash
cd /tmp/metasheet2-pact-wave-sync-1k4fiv
npx vitest run packages/core-backend/tests/contract/plm-adapter-yuantus.pact.test.ts
```

Observed result:

```text
Test Files  1 passed (1)
Tests      13 passed (13)
```

Conclusion:

- the hand-authored consumer pact artifact still matches the current adapter
  call surface

### 4. Consumer unit suites on installed dependency graph

The clean `metasheet2` worktree does not carry installed repo dependencies, so
the adapter and federation unit suites were verified against the primary
checkout's dependency graph after confirming the relevant files are identical to
`origin/main`.

File identity check:

```bash
cd /Users/huazhou/Downloads/Github/metasheet2
git diff --name-only origin/main -- \
  packages/core-backend/src/data-adapters/PLMAdapter.ts \
  packages/core-backend/tests/unit/plm-adapter-yuantus.test.ts \
  packages/core-backend/tests/unit/federation.contract.test.ts \
  packages/core-backend/tests/contract/plm-adapter-yuantus.pact.test.ts \
  packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json
```

Observed result:

- no output

Unit command:

```bash
cd /Users/huazhou/Downloads/Github/metasheet2/packages/core-backend
npx vitest run tests/unit/plm-adapter-yuantus.test.ts tests/unit/federation.contract.test.ts
```

Observed result:

```text
Test Files  2 passed (2)
Tests      33 passed (33)
Duration   7.81s
```

Key assertions covered by this batch:

- documents merge attachments + AML related documents
- documents degradation metadata is surfaced both in adapter and federation route
- BOM / approvals / substitutes / CAD / release-readiness federation contracts remain green

### 5. Compose profile render verification

Command:

```bash
cd /tmp/yuantus-mainline-closeout-*/
METASHEET2_ROOT=/tmp/metasheet2-pact-wave-sync-1k4fiv \
  bash scripts/verify_compose_sku_profiles.sh
```

Observed result:

```text
base: ok (...)
collab: ok (...)
combined: ok (...)
```

Conclusion:

- all three SKU overlays render on current mainline
- `combined` still resolves the sibling `metasheet2` checkout correctly

### 6. Runtime smoke status

Command attempted:

```bash
cd /tmp/yuantus-mainline-closeout-*/
bash scripts/verify_compose_sku_profiles_smoke.sh base
```

Observed result:

```text
postgres Error failed to resolve reference "docker.io/library/postgres:16-alpine": failed to do request: Head "https://registry-1.docker.io/v2/library/postgres/manifests/16-alpine": EOF
```

Interpretation:

- smoke harness invocation is correct
- current blocker is still external image pull availability from Docker Hub
- this does not invalidate the compose overlay design or render verification

## End State

The original integration direction is now backed by mainline code, CI gates,
and repeatable verification:

- product packaging is explicit
- contract ownership is explicit
- provider and consumer surfaces are protected
- compose overlays are real and renderable
- native workspace and federation drilldowns have crossed from plan to shipped behavior

The remaining non-code blocker in this track is external runtime image
availability for full compose smoke on this host.
