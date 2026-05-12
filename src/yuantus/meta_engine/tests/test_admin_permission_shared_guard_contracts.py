from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RELEASE_ORCHESTRATION_ROUTER = (
    ROOT / "src/yuantus/meta_engine/web/release_orchestration_router.py"
)
ITEM_COCKPIT_ROUTER = ROOT / "src/yuantus/meta_engine/web/item_cockpit_router.py"
DEDUP_ROUTER = ROOT / "src/yuantus/meta_engine/web/dedup_router.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_ADMIN_PERMISSION_ROUTER_GUARDS_20260512.md"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _local_defs(path: Path) -> set[str]:
    tree = ast.parse(_source(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_release_orchestration_and_item_cockpit_use_shared_permission_guard() -> None:
    for router_path in (RELEASE_ORCHESTRATION_ROUTER, ITEM_COCKPIT_ROUTER):
        source = _source(router_path)

        assert "require_admin_permission" in source
        assert "_ensure_admin" not in _local_defs(router_path)
        assert "Admin permission required" not in source


def test_dedup_admin_guard_remains_out_of_permission_scope() -> None:
    dedup_source = _source(DEDUP_ROUTER)

    assert "_ensure_admin" in _local_defs(DEDUP_ROUTER)
    assert 'detail="Admin required"' in dedup_source


def test_admin_permission_router_guard_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
