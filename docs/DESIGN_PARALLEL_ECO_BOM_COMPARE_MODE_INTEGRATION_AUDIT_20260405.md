# Design: ECO BOM Compare Mode Integration Audit

## Date

2026-04-05

## Scope

Audit current BOM compare + ECO surfaces to determine the remaining work for
`C3 + C4`:

- BOM compare mode switch threaded into ECO paths
- summarized/alternate compare modes propagated into ECO-facing workflows

Audit-only package. No code changes are required for this document.

## Current Capabilities

| Capability | Status | Evidence |
| --- | :---: | --- |
| BOM compare mode registry and validation | YES | `BOMService.resolve_compare_mode()` |
| BOM compare schema exposes compare modes | YES | `BOMService.compare_schema()` |
| Raw BOM compare accepts `compare_mode` | YES | `GET /bom/compare` |
| BOM delta preview/export accepts `compare_mode` | YES | `/bom/compare/delta/preview`, `/bom/compare/delta/export` |
| Summarized BOM compare/export/snapshots | YES | `/bom/compare/summarized*` |
| ECO impact accepts `compare_mode` | YES | `/eco/{eco_id}/impact`, `/impact/export` |
| ECO BOM diff accepts `compare_mode` | YES | `/eco/{eco_id}/bom-diff` |
| ECO service forwards `compare_mode` into BOM diff | YES | `ECOService.get_bom_diff()`, `analyze_impact()` |
| ECO compute-changes endpoint | PARTIAL | exists, but not compare-mode aware |
| ECO apply diagnostics / apply | YES | endpoints exist, but not compare-mode-specific |

## Audit Matrix

| Concern | Current implementation | Target parity | Gap? | Gap type | Suggested fix | Likely files |
| --- | --- | --- | :---: | --- | --- | --- |
| BOM compare mode registry | compare modes normalized in `BOMService.resolve_compare_mode()` | stable compare-mode source of truth | NO | — | none | `bom_service.py` |
| BOM compare contract | raw compare, delta preview/export, summarized compare all accept compare mode | complete standalone BOM compare contract | NO | — | none | `bom_router.py`, `bom_service.py` |
| ECO impact integration | `analyze_impact()` forwards `compare_mode` into `get_bom_diff()` | impact payload should honor selected compare mode | NO | — | none | `eco_service.py`, `eco_router.py` |
| ECO BOM diff integration | `get_bom_diff()` resolves compare mode and forwards it to BOM compare | ECO redline diff should honor selected compare mode | NO | — | none | `eco_service.py`, `eco_router.py` |
| ECO compute-changes integration | `compute_bom_changes()` uses hard-coded level-1 flattening by child id and has no compare-mode input | ECO computed change rows should optionally derive from compare-mode aware BOM diff | YES | medium code | add compare-mode aware compute path and router parameter | `eco_service.py`, `eco_router.py`, ECO tests |
| ECO apply-diagnostics linkage | apply diagnostics currently validate apply preconditions, not compare-mode compute semantics | diagnostics may optionally reference compare-mode-driven change generation, but not required for closure | PARTIAL | docs-only / future product | document as non-blocking | docs only |
| Router/test contract coverage | no dedicated ECO tests assert `compare_mode` pass-through on impact/bom-diff/compute-changes | contract-level coverage for compare-mode threading | YES | tiny-medium code | add focused router/service tests | ECO router/service tests |

## What Is Already Complete

### BOM compare line

The BOM compare cluster is already strong:

- compare mode registry exists
- mode aliases exist
- summarized compare/export/snapshot surfaces exist
- delta preview/export sits on top of compare output

This is not a BOM-compare greenfield problem.

### ECO read-side integration

The ECO read-side is already partially integrated:

- `impact`
- `impact/export`
- `bom-diff`

all expose `compare_mode` and pass it into `ECOService.get_bom_diff()`.

## Real Gap

### GAP-CI1: `compute-changes` is still legacy level-1 diff logic

`POST /eco/{eco_id}/compute-changes` currently:

- takes no `compare_mode`
- uses `get_bom_for_version(..., levels=1)`
- flattens by child item id
- compares level-1 relationship properties only

This means the ECO mutation-producing path is not aligned with the richer BOM
compare contract already available elsewhere.

This is the main remaining integration gap for `C3 + C4`.

### GAP-CI2: compare-mode threading lacks focused ECO contract tests

The code already threads `compare_mode` through ECO read-side APIs, but there
is little focused ECO test coverage proving:

- router pass-through
- service-level compare-mode forwarding
- invalid compare-mode handling on ECO routes

This is a bounded test/contract gap, not an architectural gap.

## Classification

### **CODE-CHANGE CANDIDATE**

This line is not docs-only yet.

The remaining work is bounded and medium-sized:

1. integrate compare-mode semantics into ECO `compute-changes`
2. add focused ECO compare-mode router/service tests

No large refactor is required.

## Minimum Write Set

### Package 1: `eco-compute-changes-compare-mode`

Scope:

- add optional `compare_mode` to `POST /eco/{eco_id}/compute-changes`
- thread it into service
- decide whether to keep current level-1 row model or map from compare result
- preserve existing ECOBOMChange persistence contract

Likely files:

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- focused ECO tests

Estimated size: medium
Risk: medium

### Package 2: `eco-compare-mode-contract-tests`

Scope:

- add focused tests for `impact`, `impact/export`, `bom-diff`, `compute-changes`
- assert compare-mode pass-through and invalid-mode behavior

Likely files:

- `src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py`
- new focused ECO router/service tests if needed

Estimated size: small
Risk: low

## Recommended Order

1. `eco-compute-changes-compare-mode`
2. `eco-compare-mode-contract-tests`

Reason:

- `compute-changes` is the real functional gap
- once it is aligned, tests can lock the whole ECO compare-mode contract

## Closure Verdict

This line is **not closed yet**.

The BOM compare cluster itself is already mature, and ECO read-side compare-mode
integration is mostly present. The remaining work is concentrated in
`compute-changes` plus focused ECO compare-mode contract coverage.
