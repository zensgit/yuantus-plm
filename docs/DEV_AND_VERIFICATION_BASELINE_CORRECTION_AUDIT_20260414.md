# Baseline Correction Audit

Date: 2026-04-14

## Goal

Clarify whether the current worktree branch matches the documented P0 convergence state,
or whether the P0 summary only reflects `origin/main` / platform branches.

## Branch Reality

- Current branch: `feature/claude-c43-cutted-parts-throughput`
- Current HEAD: `a50f400`
- Local `main`: `dd87f68`
- `platform/plm-core-convergence`: `1de3c4a`
- `platform/plm-p02-eco-permission-adapter`: `f71ae2b`
- `platform/plm-p03-eco-routing-change`: `43b1888`
- `origin/main`: `1c78a18`

## Divergence

Commands run:

```bash
git rev-list --left-right --count \
  feature/claude-c43-cutted-parts-throughput...platform/plm-core-convergence

git rev-list --left-right --count \
  feature/claude-c43-cutted-parts-throughput...platform/plm-p02-eco-permission-adapter

git rev-list --left-right --count \
  feature/claude-c43-cutted-parts-throughput...platform/plm-p03-eco-routing-change

git rev-list --left-right --count \
  feature/claude-c43-cutted-parts-throughput...origin/main
```

Results:

- current vs `platform/plm-core-convergence`: `6 128`
- current vs `platform/plm-p02-eco-permission-adapter`: `6 129`
- current vs `platform/plm-p03-eco-routing-change`: `6 129`
- current vs `origin/main`: `6 135`

Interpretation:

- The current feature branch is not the merged P0 baseline.
- The P0 convergence work exists in local/remote platform branches and in `origin/main`.
- The current branch is behind that baseline by a large margin.

## Code Reality Check

The P0 summary claims the following are merged:

- `#198` ECO canonical write path
- `#199` ECO permission adapter
- `#200` ECO routing change tracking

On the current feature branch, the code does not reflect that state:

- `/ecm` still uses the old change router:
  - `src/yuantus/meta_engine/web/change_router.py`
- ECO service still instantiates the allow-by-default RBAC permission manager:
  - `src/yuantus/meta_engine/services/eco_service.py`
  - `src/yuantus/security/rbac/permissions.py`
- The P0 routing-change symbols are not present in the current branch:
  - no `ECORoutingChange`
  - no `compute_routing_changes`

On `origin/main`, the same files do reflect the P0 convergence state:

- `change_router.py` is a deprecated compat shim delegating to legacy compat service
- `eco_service.py` uses `EcoPermissionAdapter`

## Conclusion

`docs/PLM_MAIN_CHAIN_CONVERGENCE_SUMMARY.md` is accurate for `origin/main`, but it is
not accurate for the current branch context.

The mismatch is not that the P0 work never existed.
The mismatch is that the current feature branch predates those merges.

## Recommended Next Step

Pick one baseline explicitly before continuing:

1. Use `origin/main` (or a clean worktree from it) as the real project baseline.
2. Keep working on the current feature branch, but stop treating it as “P0 already merged”.
3. If this feature branch must continue long-term, rebase or merge from `origin/main` first.

## Verification Notes

- Broad focused regression for recent CAD / file-lock / ECO-adjacent slices:
  - `143 passed, 1 warning`
- `py_compile` on touched integration files:
  - passed
- `Claude Code CLI` availability:
  - `claude` command exists
  - `claude -p` fails with `Not logged in · Please run /login`
