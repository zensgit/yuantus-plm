# Router-Surface-Misc Split Execution Card

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This card is the first residual code-facing cleanup after the six declared
dirty-tree domains.

## Scope

Target files:

- `src/yuantus/meta_engine/web/app_router.py`
- `src/yuantus/meta_engine/web/manufacturing_router.py`
- `src/yuantus/meta_engine/tests/test_box_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py`
- `src/yuantus/meta_engine/tests/test_router_registration_misc.py`

## Execute

```bash
git switch -c feature/router-surface-misc
git status --short -- \
  src/yuantus/meta_engine/web/app_router.py \
  src/yuantus/meta_engine/web/manufacturing_router.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py \
  src/yuantus/meta_engine/tests/test_router_registration_misc.py
git add -- \
  src/yuantus/meta_engine/web/app_router.py \
  src/yuantus/meta_engine/web/manufacturing_router.py \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py \
  src/yuantus/meta_engine/tests/test_router_registration_misc.py
git diff --cached --stat
```

## Verification

```bash
./.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py \
  src/yuantus/meta_engine/tests/test_router_registration_misc.py -q
```

## Suggested Commit

- branch: `feature/router-surface-misc`
- commit title: `feat(meta-engine): split router surface misc updates`

## Rule

- keep this split limited to router wiring and router-surface tests
- do **not** mix product-strategy docs into this branch
- do **not** mix subcontracting governance docs into this branch
- if unrelated service/model hunks appear in `app_router.py`, split or drop them

## Related References

- `docs/DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md`
- `docs/DIRTY_TREE_DOMAIN_COVERAGE_20260409.md`
- `docs/BRANCH_CLOSEOUT_SUMMARY_20260409.md`
