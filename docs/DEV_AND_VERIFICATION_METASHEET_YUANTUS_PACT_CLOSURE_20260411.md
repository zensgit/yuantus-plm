# Metasheet <-> Yuantus Pact Closure

Date: 2026-04-11

## Scope

This document closes the current Metasheet-to-Yuantus PLM federation track:

- strategy lock
- Wave 1 / 1.5 pact baseline
- Wave 2 document semantics expansion
- Wave 3 BOM / ECO approval expansion
- Wave 4 approval detail / BOM substitutes expansion
- Wave 5 CAD metadata / review workspace expansion
- post-Wave-5 CI hardening and CAD diff compatibility cleanup

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
- `metasheet2-plm-workbench` remains frozen pending separate merge review and
  must not become a second contract source

Reference docs:

- [PACT_FIRST_INTEGRATION_PLAN_20260407.md](./PACT_FIRST_INTEGRATION_PLAN_20260407.md)
- [METASHEET_REPO_SOURCE_OF_TRUTH_INVESTIGATION_20260407.md](./METASHEET_REPO_SOURCE_OF_TRUTH_INVESTIGATION_20260407.md)
- [WORKBENCH_BRANCH_FREEZE_20260408.md](./WORKBENCH_BRANCH_FREEZE_20260408.md)

### 2. Product / workflow boundary

- PLM authoritative object lifecycle remains in Yuantus
- Metasheet remains the collaboration / federation-facing shell
- Workbench is an admin/operator console and evolution base, not the short-term
  end-user workspace

Reference docs:

- [PRODUCT_SKU_MATRIX.md](./PRODUCT_SKU_MATRIX.md)
- [WORKFLOW_OWNERSHIP_RULES.md](./WORKFLOW_OWNERSHIP_RULES.md)

### 3. Document semantics

The integration treats two document concepts as distinct and intentional:

- File attachments: physical files from `GET /api/v1/file/item/{item_id}`
- AML related documents: structured `Part -> Document` relations via
  `POST /api/v1/aml/query` with `expand: ["Document Part"]`

This remains the correct model. The two data sources are orthogonal and must
not be collapsed into one semantic bucket.

## Protected Contract Surface

The current protected surface covers **29 interactions**.

### Wave 1 / 1.5 core baseline

- `POST /api/v1/auth/login`
- `GET /api/v1/health`
- `GET /api/v1/search/`
- `POST /api/v1/aml/apply`
- `GET /api/v1/bom/{id}/tree`
- `GET /api/v1/bom/compare`

### Wave 2 document semantics, readiness, and BOM analysis

- `GET /api/v1/file/item/{item_id}`
- `GET /api/v1/file/{file_id}`
- `POST /api/v1/aml/query`
- `GET /api/v1/release-readiness/items/{id}`
- `GET /api/v1/bom/{id}/where-used`
- `GET /api/v1/bom/compare/schema`

### Wave 3 / Wave 4 ECO approvals and BOM substitutes

- `GET /api/v1/eco/{id}/approvals`
- `POST /api/v1/eco/{id}/approve`
- `POST /api/v1/eco/{id}/reject`
- `GET /api/v1/eco`
- `GET /api/v1/eco/{id}`
- `GET /api/v1/bom/{relationship_id}/substitutes`
- `POST /api/v1/bom/{relationship_id}/substitutes`
- `DELETE /api/v1/bom/{relationship_id}/substitutes/{substitute_id}`

### Wave 5 CAD workspace

- `GET /api/v1/cad/files/{file_id}/properties`
- `PATCH /api/v1/cad/files/{file_id}/properties`
- `GET /api/v1/cad/files/{file_id}/view-state`
- `PATCH /api/v1/cad/files/{file_id}/view-state`
- `GET /api/v1/cad/files/{file_id}/review`
- `POST /api/v1/cad/files/{file_id}/review`
- `GET /api/v1/cad/files/{file_id}/history`
- `GET /api/v1/cad/files/{file_id}/diff`
- `GET /api/v1/cad/files/{file_id}/mesh-stats`

Canonical artifacts:

- consumer pact:
  `metasheet2/packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json`
- consumer drift test:
  `metasheet2/packages/core-backend/tests/contract/plm-adapter-yuantus.pact.test.ts`
- provider verifier:
  `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- provider pact copy:
  `contracts/pacts/metasheet2-yuantus-plm.json`

Explicitly **not** in Pact today:

- `GET /api/v1/aml/metadata/{item_type_name}`
  - strategically relevant, but still not called by `metasheet2` mainline

## CI Enforcement

Post-Wave-5 hardening adds contract gates on both sides:

- `metasheet2/.github/workflows/yuantus-pact-consumer.yml`
  - dedicated consumer gate
  - triggers only on Yuantus pact-relevant paths
  - runs `pnpm --filter @metasheet/core-backend test:contract`
  - runs `pnpm --filter @metasheet/core-backend exec vitest run tests/unit/plm-adapter-yuantus.test.ts --reporter=dot`
- `Yuantus/.github/workflows/ci.yml`
  - existing `contracts` job now installs full Python dependencies plus
    `pact-python==3.2.1`
  - executes `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
  - `run_contracts` now triggers for pact artifacts, the provider verifier,
    `cad_router.py`, and the native CAD review caller

This is the point where the integration stops depending on manual memory. Both
repos now have an explicit CI gate for the shared surface.

## Merged Delivery

### Wave 2

- `zensgit/metasheet2#787`
  - document semantics alignment on the consumer side
- `zensgit/yuantus-plm#181`
  - provider support for AML query contract shape used by document federation
- `zensgit/yuantus-plm#180`
  - release-readiness drilldown support used during live federation validation

### Wave 3

- `zensgit/metasheet2#791`
  - Wave 3 contract expansion for BOM / approvals consumer coverage
- `zensgit/yuantus-plm#182`
  - Wave 3 provider fixtures and verifier support

### Wave 3 polish

- `zensgit/metasheet2#793`
  - merged as `e3a305283a385b9e31dc0be3e31846cbda46d9b0`
  - clarified that `version` remains required in the health contract
  - aligned unit mocks with pact-required ECO fields
- `zensgit/yuantus-plm#183`
  - merged as `af4722e82633a07ac140723f403f0985039e4bf1`
  - refactored repeated provider ECO seed setup without changing behaviour

### Wave 4

- `zensgit/metasheet2#796`
  - merged as `d9b98a4d0bbdb0168afe10257a5fbed0f939cba6`
  - added approval list/detail and BOM substitutes consumer coverage
- `zensgit/yuantus-plm#185`
  - merged as `a31c0464aef2ca5a0d928f6799a7adecc8dd29eb`
  - added Wave 4 provider verification

### Wave 5

- `zensgit/metasheet2#797`
  - merged as `1b4df9ec312b48aa3caa6aa46e1b8a99cbe25ecc`
  - added CAD consumer contract coverage
- `zensgit/yuantus-plm#186`
  - merged as `26212c42c03654204c571c13b84395c50516f631`
  - added CAD provider verification

### Post-closeout hardening on mainline

- `zensgit/metasheet2#799`
  - merged as `016d26c02555ad8448e5f5cba0f64f2d620c89da`
  - added the dedicated Yuantus consumer CI gate on `metasheet2` main
- `zensgit/yuantus-plm#187`
  - merged as `cb8e167ba84f08c27bbdefc3beeb5d16ae6bb333`
  - hardened the provider CI gate and fixed the PLM workspace AML related-doc
    path drift that was breaking `playwright-esign`
- `zensgit/yuantus-plm#188`
  - merged as `4f8a34062b8dfd5a3ee742a751a44cdbcadc8da9`
  - moved workflow action majors off deprecated Node 20 runtimes and aligned
    the CI contract tests to the new baseline

## Verification

### 1. Consumer-side contract verification

Current closeout commands:

```bash
cd /tmp/metasheet2-pact-main-*/packages/core-backend
pnpm test:contract
pnpm exec vitest run tests/unit/plm-adapter-yuantus.test.ts --reporter=dot
```

Observed results on the closeout branch:

- contract tests: `16 passed`
- targeted Yuantus adapter unit tests: `19 passed`

### 2. Provider-side contract verification

Current closeout commands:

```bash
cd /tmp/yuantus-pact-main-*
/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_cad_diff_query_alias.py \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q
```

Observed results on the closeout branch:

- combined closeout verification: `9 passed`
- provider verifier remains `1 passed` inside that batch

### 2.1 Mainline re-verification after merge

After the closeout branches were merged, the shared surface was re-verified on
clean worktrees cut from `origin/main`, not from the historical feature
branches.

Commands run:

```bash
cd /tmp/metasheet2-pact-final-*/packages/core-backend
pnpm test:contract
pnpm exec vitest run tests/unit/plm-adapter-yuantus.test.ts --reporter=dot

cd /tmp/yuantus-pact-main-*
/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m pytest \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_cad_diff_query_alias.py -q
```

Observed results on main:

- `metasheet2` contract tests: `16 passed`
- `metasheet2` targeted Yuantus adapter unit tests: `19 passed`
- `Yuantus` provider verifier: `1 passed`
- `Yuantus` pact/CI guard batch: `8 passed`

This is the important distinction: the contract gate is no longer only "green
on the feature branch that introduced it". It is green again on the merged
mainline state after the later CI-hardening and GitHub Actions runtime uplift.

### 3. Deliberate break proof

The gate was proven, not assumed:

- round 1: baseline `5` failures -> deliberate break `6` failures -> revert `5`
- round 2: baseline `0` failures -> deliberate break `1` failure -> revert `0`

Canonical record:

- [PACT_DELIBERATE_BREAK_EXPERIMENT_20260408.md](./PACT_DELIBERATE_BREAK_EXPERIMENT_20260408.md)

### 4. Live federation validation

The work was not limited to synthetic contract checks. Real federation
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
- directory-level `add_source(...)` tried to parse `README.md`
- context manager `yield` exceptions were originally hidden as readiness errors
- Wave 5 caught two real CAD drifts:
  - `PATCH /view-state` must not echo request-only `refresh_preview`
  - `GET /history` needed response ordering aligned to real provider behaviour
- native CAD callers were still using legacy `other_id`
  - the route now accepts both `other_file_id` and `other_id`
  - canonical callers now send `other_file_id`
  - canonical wins when both are present

### What not to do next

- do not add endpoints to Pact just because they are strategically interesting
- do not let `metasheet2-plm-workbench` become a second contract source-of-truth
- do not merge attachments and AML related documents into one overloaded field
- do not relax required fields such as health `version` without a real consumer
  change in `metasheet2` mainline
- do not remove the legacy `other_id` alias until every native Yuantus caller
  and any downstream automation has been migrated

## Current End State

The current closure point is:

- strategy locked
- contract ownership locked
- document semantics aligned
- Wave 1 / 1.5 / 2 / 3 / 4 / 5 contract coverage landed
- pact surface locked at `28` interactions
- deliberate break proved
- live federation path validated
- CI contract gates landed on both repos
- merged mainline re-verified after PRs `#799`, `#187`, and `#188`
- native CAD diff callers normalized to canonical `other_file_id`

At this point, the Metasheet <-> Yuantus PLM federation path is not an
architectural assumption. It is a versioned, reviewable, CI-enforced
integration surface.
