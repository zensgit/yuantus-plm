from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Response

from yuantus.meta_engine.web import cad_checkin_router
from yuantus.meta_engine.web import change_router
from yuantus.meta_engine.web import equivalent_router
from yuantus.meta_engine.web import schema_router
from yuantus.meta_engine.web import store_router


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
API_DIR = ROOT / "src/yuantus/api"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_RESIDUAL_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md"
)

EXPECTED_LINES = {
    "cad_checkin_router.py": [
        "raise HTTPException(status_code=400, detail=str(e)) from e",
        "raise HTTPException(status_code=500, detail=str(e)) from e",
    ],
    "change_router.py": [
        "raise HTTPException(status_code=400, detail=str(e)) from e",
    ],
    "equivalent_router.py": [
        "raise HTTPException(status_code=404, detail=str(e)) from e",
    ],
    "schema_router.py": [
        "raise HTTPException(status_code=404, detail=str(e)) from e",
    ],
    "store_router.py": [
        "raise HTTPException(status_code=400, detail=str(e)) from e",
    ],
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_equivalent_remove_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.return_value = SimpleNamespace(
        item_type_id="Part Equivalent",
        source_id="part-1",
        related_id="part-2",
    )
    user = SimpleNamespace(id=7, roles=["engineer"])

    class AllowPermissions:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def check_permission(self, *_args: object, **_kwargs: object) -> bool:
            return True

    class FailingEquivalentService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def remove_equivalent(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("relationship missing")

    monkeypatch.setattr(equivalent_router, "MetaPermissionService", AllowPermissions)
    monkeypatch.setattr(
        equivalent_router,
        "EquivalentService",
        FailingEquivalentService,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            equivalent_router.remove_equivalent(
                "part-1",
                "rel-1",
                user=user,
                db=db,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "relationship missing"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_change_add_affected_item_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingCompatService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def add_affected_item_compat(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("legacy add rejected")

    monkeypatch.setattr(change_router, "LegacyEcmCompatService", FailingCompatService)

    with pytest.raises(HTTPException) as exc_info:
        change_router.add_affected_item(
            "eco-1",
            target_item_id="part-1",
            action="Change",
            user_id=7,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "legacy add rejected"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()


def test_store_purchase_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingStoreService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def purchase_app(self, *_args: object, **_kwargs: object) -> object:
            raise RuntimeError("purchase rejected")

    monkeypatch.setattr(store_router, "AppStoreService", FailingStoreService)

    with pytest.raises(HTTPException) as exc_info:
        store_router.purchase_app("listing-1", "Standard", db=db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "purchase rejected"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()


def test_cad_checkout_failure_preserves_exception_cause_and_rollback() -> None:
    session = MagicMock()

    class FailingCheckinManager:
        def __init__(self) -> None:
            self.session = session

        def checkout(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("checkout rejected")

    with pytest.raises(HTTPException) as exc_info:
        cad_checkin_router.checkout_document("item-1", mgr=FailingCheckinManager())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "checkout rejected"
    assert isinstance(exc_info.value.__cause__, ValueError)
    session.rollback.assert_called_once_with()


def test_schema_refresh_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingMetaSchemaService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def update_cached_schema(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("schema missing")

    monkeypatch.setattr(schema_router, "MetaSchemaService", FailingMetaSchemaService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            schema_router.refresh_item_type_schema(
                "Part",
                db=db,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "schema missing"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_residual_router_exception_chaining_is_source_pinned() -> None:
    for filename, expected_lines in EXPECTED_LINES.items():
        source = _source(WEB_DIR / filename)
        for expected_line in expected_lines:
            assert expected_line in source


def test_meta_web_and_api_have_no_bare_stringified_exception_mappings() -> None:
    offenders: list[str] = []
    for directory in (WEB_DIR, API_DIR):
        for path in sorted(directory.rglob("*.py")):
            source = _source(path)
            for line_no, line in enumerate(source.splitlines(), start=1):
                stripped = line.strip()
                if (
                    stripped.startswith("raise HTTPException(")
                    and "detail=str(" in stripped
                    and " from " not in stripped
                ):
                    offenders.append(f"{path.relative_to(ROOT)}:{line_no}:{stripped}")

    assert offenders == []


def test_residual_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    doc_index = _source(DOC_INDEX)

    assert "test_residual_router_exception_chaining_closeout.py" in workflow
    assert DEV_VERIFICATION_DOC in doc_index
    assert (ROOT / DEV_VERIFICATION_DOC).exists()
