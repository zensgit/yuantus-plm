from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import HTTPException

from yuantus.api.dependencies.auth import CurrentUser, require_admin_permission


ROOT = Path(__file__).resolve().parents[4]
ESIGN_ROUTER = ROOT / "src/yuantus/meta_engine/web/esign_router.py"
RELEASE_READINESS_ROUTER = (
    ROOT / "src/yuantus/meta_engine/web/release_readiness_router.py"
)
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_ADMIN_PERMISSION_GUARD_FOLLOWUP_20260512.md"
)


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


def _local_defs(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_require_admin_permission_allows_admin_role() -> None:
    user = _current_user(roles=[" Admin "])

    assert require_admin_permission(user) is user


def test_require_admin_permission_allows_superuser_flag() -> None:
    user = _current_user(roles=["viewer"], is_superuser=True)

    assert require_admin_permission(user) is user


def test_require_admin_permission_rejects_non_admin_with_existing_detail() -> None:
    user = _current_user(roles=["viewer"])

    with pytest.raises(HTTPException) as exc_info:
        require_admin_permission(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin permission required"


@pytest.mark.parametrize("router_path", [ESIGN_ROUTER, RELEASE_READINESS_ROUTER])
def test_routers_import_shared_admin_permission_guard(router_path: Path) -> None:
    source = router_path.read_text(encoding="utf-8")

    assert "require_admin_permission" in source
    assert "_ensure_admin" not in _local_defs(router_path)
    assert "Admin permission required" not in source


def test_admin_permission_guard_followup_is_ci_wired_and_doc_indexed() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    index = DOC_INDEX.read_text(encoding="utf-8")

    assert (
        "src/yuantus/meta_engine/tests/test_admin_permission_guard_followup_contracts.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
