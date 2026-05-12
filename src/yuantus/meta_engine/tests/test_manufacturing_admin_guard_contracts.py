from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MANUFACTURING_ROUTER = ROOT / "src/yuantus/meta_engine/web/manufacturing_router.py"
DEDUP_ROUTER = ROOT / "src/yuantus/meta_engine/web/dedup_router.py"
AUTH_DEPENDENCY = ROOT / "src/yuantus/api/dependencies/auth.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_MANUFACTURING_ADMIN_GUARD_FOLLOWUP_20260512.md"
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


def test_manufacturing_router_uses_shared_admin_role_guard() -> None:
    source = _source(MANUFACTURING_ROUTER)

    assert "require_admin_user" in source
    assert source.count("require_admin_user(user)") == 16
    assert "_ensure_admin" not in _local_defs(MANUFACTURING_ROUTER)
    assert "Admin role required" not in source


def test_shared_admin_role_guard_preserves_manufacturing_detail() -> None:
    auth_source = _source(AUTH_DEPENDENCY)

    assert "def require_admin_user" in auth_source
    assert 'detail="Admin role required"' in auth_source


def test_dedup_admin_guard_remains_distinct_and_out_of_scope() -> None:
    dedup_source = _source(DEDUP_ROUTER)

    assert "_ensure_admin" in _local_defs(DEDUP_ROUTER)
    assert 'detail="Admin required"' in dedup_source


def test_manufacturing_admin_guard_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
