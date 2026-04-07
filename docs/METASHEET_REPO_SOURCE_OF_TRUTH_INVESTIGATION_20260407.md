# Metasheet Repo Source-of-Truth Investigation

## Purpose

Decide which working directory of the Metasheet codebase should host the consumer Pact tests for the Yuantus integration, so that contract authoring is single-sourced rather than double-written.

This is a prerequisite for executing the Pact-First plan in `docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md`.

## Candidates

Two working directories on disk both contain a Yuantus-aware `PLMAdapter.ts`:

| Path | Branch | Distance from origin/main |
|---|---|---|
| `/Users/huazhou/Downloads/Github/metasheet2` | `codex/approval-bridge-plm-phase1-20260404` | **1 commit ahead** |
| `/Users/huazhou/Downloads/Github/metasheet2-plm-workbench` | `codex/plm-workbench-collab-20260312` | **384 commits ahead** |

Both share the same git origin: `git@github.com:zensgit/metasheet2.git`. They are not forks; they are two working trees of the same repository on different branches.

## Adapter Comparison

| Property | `metasheet2/` | `metasheet2-plm-workbench/` |
|---|---|---|
| `PLMAdapter.ts` line count | 1991 | 1955 |
| Last touched (file) | 2026-03-19 | 2026-03-26 |
| Total commits touching the file | 12 | 12 |
| Calls `POST /api/v1/aml/apply` | Yes (lines 1188, 1211) | Yes |
| Calls `GET /api/v1/aml/metadata/{type}` | (TBD — see open questions) | (TBD) |
| Has `getApprovalById()` | **Yes** | No |
| `approveApproval` signature | `(id, comment?)` | `(id, **version**, comment?)` |
| `rejectApproval` signature | `(id, comment)` | `(id, **version**, comment)` |
| Optimistic locking on approval mutations | No | **Yes (version field)** |

The two adapters are not identical — they have **divergent improvements**:

- `metasheet2/` has additional `getApprovalById()` lookup that workbench lacks
- `metasheet2-plm-workbench/` has version-aware approve/reject for optimistic concurrency control that mainline lacks

The combined `diff` is 59 lines, scoped almost entirely to the approval section.

## Recommendation

**Author the consumer pact in `metasheet2/` mainline.**

Reasons:
1. **Branch tracks origin/main** (1 commit ahead vs 384). Long-term maintenance will gravitate here.
2. **Single zensgit/metasheet2 origin**, no fork ambiguity.
3. **Workbench is a feature spike**, not a parallel product line. Treating it as a contract source of truth would create double-write maintenance cost.
4. **Codex's PACT_FIRST plan already recommends this** (`docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md` §"Source-Of-Truth Decision For Consumer Pact").

## Forward-Compatibility Caveat

The workbench branch's optimistic-locking improvements are real and good. They will likely merge back to mainline at some point. To avoid the pact breaking when that happens:

- Encode the `version` field in `approveApproval` / `rejectApproval` request bodies as **optional** in the pact (`Matchers.like` with the field absent in the example body)
- Document in the consumer pact spec file that the version field is "additive, optional, expected to become required in a future contract version"
- When workbench's optimistic locking actually lands in mainline, bump to a Wave 2 contract that requires the field

This keeps the Wave 1 pact valid before and after the merge.

## Workbench Spike Hygiene

To prevent the spike from drifting indefinitely:

1. **Track merge debt explicitly**. Today the spike is 384 commits ahead of main; that is too much for safe rebase. Suggest cherry-picking specific improvements (notably the optimistic-locking work) to mainline as small targeted PRs.
2. **Do not run a parallel pact suite in the workbench branch**. If a pact test is needed locally for spike work, copy the mainline pact JSON into the workbench's contracts dir; do not author new ones there.
3. **Document the spike's purpose** in the workbench branch's README so future readers know it's not a parallel main.

## Open Questions for Owners

1. Is `metasheet2-plm-workbench` actively used by any deployment, or is it pure dev workbench? If it's deployed somewhere, the source-of-truth recommendation may need revisiting.
2. Who owns merging workbench improvements back to mainline? Without a named owner, the spike will keep drifting.
3. Are there other long-running working trees (`metasheet2-deploy-fix-20260326`, `metasheet2-multitable-next`, `metasheet2-sync`) that also call PLM endpoints? They should be checked before final pact freeze.

## Verification Performed

- Provider verifier sanity check: `pytest src/yuantus/api/tests/test_pact_provider_yuantus_plm.py -q` → `1 skipped in 3.34s` ✅
- Both adapters confirmed to call `/api/v1/aml/apply` (`Grep` of both files)
- Yuantus side confirmed to implement `/api/v1/aml/apply` at `src/yuantus/meta_engine/web/router.py:22`
- Yuantus side confirmed to implement `/api/v1/aml/metadata/{item_type_name}` at `src/yuantus/meta_engine/web/router.py:52` (already exists, no need to add)

## Decision Status (UPDATED 2026-04-07)

- ✅ Recommendation accepted: consumer pact authored in `metasheet2/` mainline
- ✅ `metasheet2-plm-workbench` branch is **frozen**: no new pact authoring there. Any improvements (notably the version-aware approve/reject) will be cherry-picked back to mainline before that pact wave lands.
- ✅ Wave 1 pact file written and tested:
  - `metasheet2/packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json`
  - Synced copy at `Yuantus/contracts/pacts/metasheet2-yuantus-plm.json`
  - Vitest sanity test at `metasheet2/.../tests/contract/plm-adapter-yuantus.pact.test.ts` → **6 tests passing**
  - Yuantus provider verifier at `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py` → still `1 skipped`, awaiting `pact-python` install (deferred — Python dep change requires explicit approval)

## Drift Caught On Day One

The contract gate fired on its first run. The hand-authored pact initially included `GET /api/v1/aml/metadata/{type}` because codex's `PACT_FIRST_INTEGRATION_PLAN_20260407.md` lists it as a Wave 1 P0 endpoint. The vitest drift test failed with:

> `PLMAdapter.ts no longer references /api/v1/aml/metadata/; pact has drifted from the consumer.`

A grep of `metasheet2/packages/core-backend/src` confirmed **no caller for that endpoint**. The endpoint exists in Yuantus (`router.py:52`) and is intended for front-end form rendering, but PLMAdapter does not yet use it. Per the contract-first principle, the endpoint was removed from Wave 1 and parked for Wave 1.5, to be added back as soon as PLMAdapter starts calling it.

**This is exactly the kind of bug the contract-first plan exists to catch.** It happened on the first hour of the first day. The cost of catching it now (small documentation correction + 3-line code edit) is negligible compared to the cost of discovering after a week of feature work that the pact does not match the consumer.

Recommended follow-up for codex: update `docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md` to move `aml/metadata` from Wave 1 P0 to "Wave 1.5: anticipated, not yet adopted by consumer", with a note that the move is driven by consumer-side grep, not by removing the endpoint from the long-term plan.

## Final Wave 1 Endpoint List (verified against PLMAdapter.ts grep)

| # | Method | Path | PLMAdapter.ts call site |
|---|---|---|---|
| 1 | POST | `/api/v1/auth/login` | line 718 (`fetchYuantusToken`) |
| 2 | GET | `/api/v1/health` | line 752 (`healthCheck`) |
| 3 | GET | `/api/v1/search/` | lines 808, 989 |
| 4 | POST | `/api/v1/aml/apply` | lines 1188, 1211 (`getProductById` detail fetch) |
| 5 | GET | `/api/v1/bom/{id}/tree` | line 1313 |
| 6 | GET | `/api/v1/bom/compare` | line 1573 |

(Wave 2 endpoints are documented separately in `docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md`.)
