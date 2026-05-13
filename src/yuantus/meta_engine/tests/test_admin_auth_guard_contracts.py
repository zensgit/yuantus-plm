from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from yuantus.api.dependencies import admin_auth
from yuantus.api.dependencies.auth import Identity


ROOT = Path(__file__).resolve().parents[4]
ADMIN_ROUTER = ROOT / "src/yuantus/api/routers/admin.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_ADMIN_AUTH_GUARD_CONSOLIDATION_20260512.md"
)


def _identity(*, tenant_id: str = "tenant-1", is_superuser: bool = False) -> Identity:
    return Identity(
        user_id=1,
        tenant_id=tenant_id,
        org_id="org-1",
        username="tester",
        email="tester@example.com",
        is_superuser=is_superuser,
    )


def _assert_http_error(exc: HTTPException, status_code: int, detail: str) -> None:
    assert exc.status_code == status_code
    assert exc.detail == detail


def test_require_superuser_allows_superuser() -> None:
    identity = _identity(is_superuser=True)

    assert admin_auth.require_superuser(identity) is identity


def test_require_superuser_rejects_non_superuser() -> None:
    with pytest.raises(HTTPException) as exc_info:
        admin_auth.require_superuser(_identity())

    _assert_http_error(exc_info.value, 403, "Superuser required")


def test_require_platform_admin_rejects_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_auth,
        "get_settings",
        lambda: SimpleNamespace(PLATFORM_ADMIN_ENABLED=False, PLATFORM_TENANT_ID="platform"),
    )

    with pytest.raises(HTTPException) as exc_info:
        admin_auth.require_platform_admin(_identity(tenant_id="platform", is_superuser=True))

    _assert_http_error(exc_info.value, 403, "Platform admin disabled")


def test_require_platform_admin_rejects_wrong_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_auth,
        "get_settings",
        lambda: SimpleNamespace(PLATFORM_ADMIN_ENABLED=True, PLATFORM_TENANT_ID="platform"),
    )

    with pytest.raises(HTTPException) as exc_info:
        admin_auth.require_platform_admin(_identity(tenant_id="tenant-1", is_superuser=True))

    _assert_http_error(exc_info.value, 403, "Platform admin required")


def test_require_platform_admin_allows_platform_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_auth,
        "get_settings",
        lambda: SimpleNamespace(PLATFORM_ADMIN_ENABLED=True, PLATFORM_TENANT_ID="platform"),
    )
    identity = _identity(tenant_id="platform", is_superuser=True)

    assert admin_auth.require_platform_admin(identity) is identity


def test_require_org_admin_allows_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    identity = _identity(is_superuser=True)
    org_calls: list[tuple[object, str, str]] = []

    def fake_get_org(db: object, tenant_id: str, org_id: str) -> object:
        org_calls.append((db, tenant_id, org_id))
        return object()

    class FailingAuthService:
        def __init__(self, db: object) -> None:
            raise AssertionError("superuser path must not query membership roles")

    monkeypatch.setattr(admin_auth, "_get_org", fake_get_org)
    monkeypatch.setattr(admin_auth, "AuthService", FailingAuthService)

    assert admin_auth.require_org_admin("org-1", identity, object()) is identity
    assert [(call[1], call[2]) for call in org_calls] == [("tenant-1", "org-1")]


@pytest.mark.parametrize("role", ["admin", "org_admin"])
def test_require_org_admin_allows_admin_roles(
    monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    identity = _identity()

    monkeypatch.setattr(admin_auth, "_get_org", lambda db, tenant_id, org_id: object())

    class FakeAuthService:
        def __init__(self, db: object) -> None:
            self.db = db

        def get_roles_for_user_org(
            self, *, tenant_id: str, org_id: str, user_id: int
        ) -> list[str]:
            assert (tenant_id, org_id, user_id) == ("tenant-1", "org-1", 1)
            return [role]

    monkeypatch.setattr(admin_auth, "AuthService", FakeAuthService)

    assert admin_auth.require_org_admin("org-1", identity, object()) is identity


def test_require_org_admin_rejects_non_admin_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_auth, "_get_org", lambda db, tenant_id, org_id: object())

    class FakeAuthService:
        def __init__(self, db: object) -> None:
            self.db = db

        def get_roles_for_user_org(
            self, *, tenant_id: str, org_id: str, user_id: int
        ) -> list[str]:
            return ["viewer"]

    monkeypatch.setattr(admin_auth, "AuthService", FakeAuthService)

    with pytest.raises(HTTPException) as exc_info:
        admin_auth.require_org_admin("org-1", _identity(), object())

    _assert_http_error(exc_info.value, 403, "Org admin required")


def test_require_org_admin_rejects_membership_lookup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(admin_auth, "_get_org", lambda db, tenant_id, org_id: object())

    class FailingAuthService:
        def __init__(self, db: object) -> None:
            self.db = db

        def get_roles_for_user_org(
            self, *, tenant_id: str, org_id: str, user_id: int
        ) -> list[str]:
            raise RuntimeError("identity store unavailable")

    monkeypatch.setattr(admin_auth, "AuthService", FailingAuthService)

    with pytest.raises(HTTPException) as exc_info:
        admin_auth.require_org_admin("org-1", _identity(), object())

    _assert_http_error(exc_info.value, 403, "Org admin required")
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_admin_router_imports_shared_guards_not_local_definitions() -> None:
    source = ADMIN_ROUTER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    local_defs = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "from yuantus.api.dependencies.admin_auth import (" in source
    assert "get_current_identity" not in source
    assert not {
        "require_superuser",
        "require_platform_admin",
        "require_org_admin",
        "_get_org",
    } & local_defs


def test_admin_auth_guard_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    index = DOC_INDEX.read_text(encoding="utf-8")

    assert "src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py" in workflow
    assert DEV_VERIFICATION_DOC in index
