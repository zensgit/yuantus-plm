from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import HTTPException

from yuantus.api.dependencies.auth import CurrentUser, require_admin_access


ROOT = Path(__file__).resolve().parents[4]
DEDUP_ROUTER = ROOT / "src/yuantus/meta_engine/web/dedup_router.py"
AUTH_DEPENDENCY = ROOT / "src/yuantus/api/dependencies/auth.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = "docs/DEV_AND_VERIFICATION_DEDUP_ADMIN_GUARD_FOLLOWUP_20260512.md"


def _current_user(*, roles: list[str], is_superuser: bool = False) -> CurrentUser:
    return CurrentUser(
        id=1,
        tenant_id="tenant-1",
        org_id="org-1",
        username="tester",
        email="tester@example.com",
        roles=roles,
        is_superuser=is_superuser,
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


def test_require_admin_access_allows_admin_role() -> None:
    user = _current_user(roles=[" Admin "])

    assert require_admin_access(user) is user


def test_require_admin_access_allows_superuser_flag() -> None:
    user = _current_user(roles=["viewer"], is_superuser=True)

    assert require_admin_access(user) is user


def test_require_admin_access_rejects_non_admin_with_dedup_detail() -> None:
    user = _current_user(roles=["viewer"])

    with pytest.raises(HTTPException) as exc_info:
        require_admin_access(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin required"


def test_dedup_router_uses_shared_admin_access_guard() -> None:
    source = _source(DEDUP_ROUTER)

    assert "require_admin_access" in source
    assert source.count("require_admin_access(user)") == 15
    assert "_ensure_admin" not in _local_defs(DEDUP_ROUTER)
    assert "Admin required" not in source


def test_shared_admin_access_guard_owns_dedup_detail() -> None:
    auth_source = _source(AUTH_DEPENDENCY)

    assert "def require_admin_access" in auth_source
    assert 'detail="Admin required"' in auth_source


def test_dedup_admin_guard_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert "src/yuantus/meta_engine/tests/test_dedup_admin_guard_contracts.py" in workflow
    assert DEV_VERIFICATION_DOC in index
