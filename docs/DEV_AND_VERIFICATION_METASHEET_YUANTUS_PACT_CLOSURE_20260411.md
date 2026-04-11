# Metasheet <-> Yuantus Pact Closure

Date: 2026-04-11

## Scope

This document closes the current Metasheet-to-Yuantus PLM federation track:

- strategy lock
- Wave 1 and Wave 1.5 pact baseline
- document semantics alignment
- Wave 3 BOM / approvals pact expansion
- follow-up polish and branch cleanup

The governing rule stayed unchanged through every wave:

- shared contract
- separate implementations
- CI-enforced compatibility

This work explicitly did **not** introduce a shared runtime library between
Python/FastAPI Yuantus and TypeScript/Node Metasheet.

## Design Lock

### 1. Repo and contract ownership

- Consumer pact source-of-truth: `metasheet2`
- Provider verifier source-of-truth: `Yuantus`
- `metasheet2-plm-workbench` is frozen pending separate merge review, not used
  as a second consumer contract source

Reference docs:

- [PACT_FIRST_INTEGRATION_PLAN_20260407.md](./PACT_FIRST_INTEGRATION_PLAN_20260407.md)
- [METASHEET_REPO_SOURCE_OF_TRUTH_INVESTIGATION_20260407.md](./METASHEET_REPO_SOURCE_OF_TRUTH_INVESTIGATION_20260407.md)
- [WORKBENCH_BRANCH_FREEZE_20260408.md](./WORKBENCH_BRANCH_FREEZE_20260408.md)

### 2. Product / workflow boundary

- PLM authoritative object lifecycle remains in Yuantus
- Metasheet stays the collaboration / federation-facing shell
- Workbench is treated as an admin/operator console and evolution base, not the
  short-term end-user workspace

Reference docs:

- [PRODUCT_SKU_MATRIX.md](./PRODUCT_SKU_MATRIX.md)
- [WORKFLOW_OWNERSHIP_RULES.md](./WORKFLOW_OWNERSHIP_RULES.md)

### 3. Document semantics

The integration now treats two document concepts as distinct and intentional:

- File attachments: physical files from `GET /api/v1/file/item/{item_id}`
- AML related documents: structured `Part -> Document` relations via
  `POST /api/v1/aml/query` with `expand: ["Document Part"]`

This is the correct model. The two data sources are orthogonal and must not be
collapsed into one semantic bucket.

### 4. Protected contract surface

After the completed waves, the protected surface covers 14 interactions across
the following public routes:

- `POST /api/v1/auth/login`
- `GET /api/v1/health`
- `GET /api/v1/search/`
- `POST /api/v1/aml/apply`
- `POST /api/v1/aml/query`
- `GET /api/v1/file/item/{item_id}`
- `GET /api/v1/bom/{id}/tree`
- `GET /api/v1/bom/{id}/where-used`
- `GET /api/v1/bom/compare`
- `GET /api/v1/bom/compare/schema`
- `GET /api/v1/eco/{id}/approvals`
- `POST /api/v1/eco/{id}/approve`
- `POST /api/v1/eco/{id}/reject`
- `GET /api/v1/release-readiness/items/{id}`

The consumer artifact lives in `metasheet2`:

- `packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json`
- `packages/core-backend/tests/contract/plm-adapter-yuantus.pact.test.ts`

The provider verifier lives in `Yuantus`:

- `contracts/pacts/metasheet2-yuantus-plm.json`
- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`

## Merged Delivery

### Core PRs

- `zensgit/metasheet2#787`
  - document semantics alignment on the consumer side
- `zensgit/yuantus-plm#181`
  - provider support for AML query contract shape used by document federation
- `zensgit/yuantus-plm#180`
  - release-readiness drilldown route support used in Phase 0.6 validation
- `zensgit/metasheet2#791`
  - Wave 3 contract expansion for BOM / approvals consumer coverage
- `zensgit/yuantus-plm#182`
  - Wave 3 provider fixtures and verifier support

### Follow-up polish PRs

- `zensgit/metasheet2#793`
  - merged as `e3a305283a385b9e31dc0be3e31846cbda46d9b0`
  - clarified that `version` remains required in mainline health contract
  - aligned approve/reject unit mocks with pact fields such as `approved_at`
    and `created_at`
- `zensgit/yuantus-plm#183`
  - merged as `af4722e82633a07ac140723f403f0985039e4bf1`
  - refactored repeated provider ECO seed setup without changing behavior

### Branch cleanup

- `codex/pact-wave3-polish-20260411` was auto-deleted after merge
- `codex/pact-wave3-provider-polish-20260411` was deleted after merge
- `metasheet2-plm-workbench` freeze marker remains intentional and should not
  be reversed casually

## Verification

### 1. Consumer-side contract verification

Executed in clean `metasheet2` worktrees during Wave 3 and follow-up polish.

Representative commands:

```bash
cd /tmp/metasheet2-wave3-bom-wtFw5I/packages/core-backend
npx vitest run \
  tests/contract/plm-adapter-yuantus.pact.test.ts \
  tests/unit/plm-adapter-yuantus.test.ts \
  tests/unit/federation.contract.test.ts \
  tests/unit/approvals-bridge-routes.test.ts

cd /tmp/metasheet2-wave3-polish-7LXelS/packages/core-backend
npx vitest run \
  tests/contract/plm-adapter-yuantus.pact.test.ts \
  tests/unit/plm-adapter-yuantus.test.ts
```

Observed results:

- Wave 3 expansion run: `54 passed`
- polish run: `24 passed`

### 2. Provider-side pact verification

Executed in clean `Yuantus` worktrees:

```bash
cd /tmp/yuantus-wave3-bom-yQA65C
./.venv/bin/python -m pytest src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q

cd /tmp/yuantus-wave3-polish-JmmyiS
./.venv/bin/python -m pytest src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q
```

Observed results:

- Wave 3 expansion run: `1 passed`
- polish run: `1 passed`

### 3. Deliberate break proof

The gate was proven twice, not assumed:

- round 1: baseline `5` failures -> deliberate break `6` failures -> revert `5`
- round 2: baseline `0` failures -> deliberate break `1` failure -> revert `0`

Canonical record:

- [PACT_DELIBERATE_BREAK_EXPERIMENT_20260408.md](./PACT_DELIBERATE_BREAK_EXPERIMENT_20260408.md)

### 4. Live federation validation

The work was not limited to synthetic contract checks. Real Phase 0 federation
validation was also completed against running Yuantus and Metasheet instances:

- Yuantus health probe passed
- Metasheet federation connect passed
- product list returned real Yuantus parts
- product detail opened successfully
- BOM route returned valid structure
- ECO approvals route returned valid approval data
- file attachment route returned real attachment data for the document demo item

The important consequence is that contract coverage and live traffic agreed on
the same public shapes.

## Operational Notes

### Bugs caught and fixed along the way

- `pact-python` rejects host mismatch between `127.0.0.1` and `localhost`
- directory-level `add_source(...)` mistakenly tried to parse `README.md`
- context manager `yield` exceptions were originally hidden as readiness errors
- some unit mocks drifted from pact-required fields
- repeated provider seed setup had become unnecessarily error-prone

These are now part of the documented baseline and should not be reintroduced.

### What not to do next

- do not add endpoints to Pact just because they are strategically interesting
- do not let `metasheet2-plm-workbench` become a second contract source-of-truth
- do not merge attachments and AML related documents into one overloaded field
- do not relax required fields such as health `version` without a real consumer
  change in `metasheet2` mainline

## Current End State

The current closure point is:

- strategy locked
- contract ownership locked
- document semantics aligned
- Wave 1 / 1.5 / 3 contract coverage landed
- deliberate break proved
- live federation path validated
- follow-up polish merged on both repos

At this point, the Metasheet <-> Yuantus PLM federation path is no longer an
architectural assumption. It is a versioned, tested, reviewable integration
surface.
