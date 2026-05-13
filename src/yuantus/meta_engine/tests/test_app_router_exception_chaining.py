from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import app_router


ROOT = Path(__file__).resolve().parents[4]
APP_ROUTER = ROOT / "src/yuantus/meta_engine/web/app_router.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_APP_ROUTER_EXCEPTION_CHAINING_20260512.md"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_register_app_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingAppService:
        def __init__(self, db_session: object) -> None:
            self.db_session = db_session

        def register_app(self, manifest: dict[str, object], installer_id: int) -> object:
            raise RuntimeError("invalid manifest")

    monkeypatch.setattr(app_router, "AppService", FailingAppService)

    with pytest.raises(HTTPException) as exc_info:
        app_router.register_app({"name": "bad"}, installer_id=7, db=db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "invalid manifest"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_create_point_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingAppService:
        def __init__(self, db_session: object) -> None:
            self.db_session = db_session

        def create_extension_point(self, name: str, description: str) -> object:
            raise ValueError("duplicate extension point")

    monkeypatch.setattr(app_router, "AppService", FailingAppService)

    with pytest.raises(HTTPException) as exc_info:
        app_router.create_point("cad.panel", "CAD panel", db=db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "duplicate extension point"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_app_router_success_paths_still_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()

    class SuccessfulAppService:
        def __init__(self, db_session: object) -> None:
            self.db_session = db_session

        def register_app(self, manifest: dict[str, object], installer_id: int) -> object:
            return SimpleNamespace(id="app-1", name=manifest["name"])

        def create_extension_point(self, name: str, description: str) -> object:
            return SimpleNamespace(id="point-1", name=name)

    monkeypatch.setattr(app_router, "AppService", SuccessfulAppService)

    assert app_router.register_app({"name": "viewer"}, installer_id=7, db=db) == {
        "status": "success",
        "app_id": "app-1",
        "name": "viewer",
    }
    assert app_router.create_point("cad.panel", "CAD panel", db=db) == {
        "id": "point-1",
        "name": "cad.panel",
    }
    assert db.commit.call_count == 2
    db.rollback.assert_not_called()


def test_app_router_exception_chaining_is_source_pinned() -> None:
    source = _source(APP_ROUTER)

    assert source.count("raise HTTPException(status_code=400, detail=str(e)) from e") == 2


def test_app_router_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert "src/yuantus/meta_engine/tests/test_app_router_exception_chaining.py" in workflow
    assert DEV_VERIFICATION_DOC in index
