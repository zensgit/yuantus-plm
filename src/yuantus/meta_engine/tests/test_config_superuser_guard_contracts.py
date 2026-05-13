from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies import admin_auth
from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.config.settings import get_settings
from yuantus.database import get_db


ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROUTER = ROOT / "src/yuantus/meta_engine/web/config_router.py"
ADMIN_AUTH = ROOT / "src/yuantus/api/dependencies/admin_auth.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = "docs/DEV_AND_VERIFICATION_CONFIG_SUPERUSER_GUARD_20260512.md"


@pytest.fixture(autouse=True)
def _auth_mode_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _current_user(*, is_superuser: bool) -> CurrentUser:
    return CurrentUser(
        id=1,
        tenant_id="tenant-1",
        org_id="org-1",
        username="tester",
        email="tester@example.com",
        roles=["viewer"],
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


def _client_with_user(user: CurrentUser) -> TestClient:
    app = create_app()
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_require_superuser_accepts_current_user_direct_call() -> None:
    user = _current_user(is_superuser=True)

    assert admin_auth.require_superuser(user) is user


def test_require_superuser_rejects_current_user_with_existing_detail() -> None:
    user = _current_user(is_superuser=False)

    with pytest.raises(HTTPException) as exc_info:
        admin_auth.require_superuser(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Superuser required"


def test_config_router_uses_shared_superuser_guard() -> None:
    source = _source(CONFIG_ROUTER)

    assert "require_superuser" in source
    assert source.count("require_superuser(user)") == 9
    assert "_ensure_superuser" not in _local_defs(CONFIG_ROUTER)
    assert "Superuser required" not in source


def test_config_write_route_still_rejects_non_superuser() -> None:
    client = _client_with_user(_current_user(is_superuser=False))

    response = client.post(
        "/api/v1/config/option-sets",
        json={"name": "Finish", "is_active": True},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Superuser required"


def test_admin_auth_owns_superuser_detail() -> None:
    source = _source(ADMIN_AUTH)

    assert "def require_superuser" in source
    assert 'detail="Superuser required"' in source


def test_config_superuser_guard_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert "src/yuantus/meta_engine/tests/test_config_superuser_guard_contracts.py" in workflow
    assert DEV_VERIFICATION_DOC in index
