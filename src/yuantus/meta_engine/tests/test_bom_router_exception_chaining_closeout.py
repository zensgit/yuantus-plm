from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import bom_children_router
from yuantus.meta_engine.web import bom_compare_router
from yuantus.meta_engine.web import bom_obsolete_rollup_router
from yuantus.meta_engine.web import bom_substitutes_router
from yuantus.meta_engine.web import bom_tree_router


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_BOM_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md"
)

EXPECTED_LINES = {
    "bom_tree_router.py": [
        "raise HTTPException(status_code=404, detail=str(e)) from e",
        "raise HTTPException(status_code=400, detail=str(e)) from e",
    ],
    "bom_children_router.py": [
        "raise HTTPException(status_code=400, detail=str(e)) from e",
        "raise HTTPException(status_code=status_code, detail=str(e)) from e",
    ],
    "bom_obsolete_rollup_router.py": [
        "raise HTTPException(status_code=400, detail=str(e)) from e",
    ],
    "bom_substitutes_router.py": [
        "raise HTTPException(status_code=404, detail=str(e)) from e",
    ],
    "bom_compare_router.py": [
        "raise HTTPException(status_code=404, detail=str(e)) from e",
        "raise HTTPException(status_code=400, detail=str(exc)) from exc",
    ],
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=1, roles=["admin"])


class AllowAllPermissions:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def check_permission(self, *_args: object, **_kwargs: object) -> bool:
        return True


def test_bom_tree_version_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingBOMService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def get_bom_for_version(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("unknown version")

    monkeypatch.setattr(bom_tree_router, "BOMService", FailingBOMService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(bom_tree_router.get_bom_by_version("version-1", levels=10, db=db))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "unknown version"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_bom_tree_convert_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.return_value = SimpleNamespace(item_type_id="Part")

    class FailingConversionService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def convert_ebom_to_mbom(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("conversion rejected")

    monkeypatch.setattr(bom_tree_router, "MetaPermissionService", AllowAllPermissions)
    monkeypatch.setattr(bom_tree_router, "BOMConversionService", FailingConversionService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            bom_tree_router.convert_ebom_to_mbom(
                bom_tree_router.ConvertBomRequest(root_id="part-1"),
                user=_user(),
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "conversion rejected"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_bom_children_add_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.side_effect = [
        SimpleNamespace(id="parent-1", item_type_id="Part", state="Draft"),
        SimpleNamespace(id="Part"),
    ]

    class FailingBOMService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def add_child(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("bad child")

    monkeypatch.setattr(bom_children_router, "BOMService", FailingBOMService)
    monkeypatch.setattr(bom_children_router, "MetaPermissionService", AllowAllPermissions)
    monkeypatch.setattr(
        bom_children_router,
        "is_item_locked",
        lambda *_args, **_kwargs: (False, None),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            bom_children_router.add_bom_child(
                "parent-1",
                bom_children_router.AddChildRequest(child_id="child-1"),
                user=_user(),
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "bad child"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_bom_children_remove_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.side_effect = [
        SimpleNamespace(id="parent-1", item_type_id="Part", state="Draft"),
        SimpleNamespace(id="Part"),
    ]

    class FailingBOMService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def remove_child(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("missing relationship")

    monkeypatch.setattr(bom_children_router, "BOMService", FailingBOMService)
    monkeypatch.setattr(bom_children_router, "MetaPermissionService", AllowAllPermissions)
    monkeypatch.setattr(
        bom_children_router,
        "is_item_locked",
        lambda *_args, **_kwargs: (False, None),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            bom_children_router.remove_bom_child(
                "parent-1",
                "child-1",
                uom=None,
                user=_user(),
                db=db,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "missing relationship"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_bom_obsolete_resolve_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.return_value = SimpleNamespace(id="root-1", item_type_id="Part")

    class FailingObsoleteService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def resolve(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("bad obsolete mode")

    monkeypatch.setattr(
        bom_obsolete_rollup_router,
        "MetaPermissionService",
        AllowAllPermissions,
    )
    monkeypatch.setattr(
        bom_obsolete_rollup_router,
        "BOMObsoleteService",
        FailingObsoleteService,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            bom_obsolete_rollup_router.resolve_obsolete_bom(
                "root-1",
                bom_obsolete_rollup_router.ObsoleteResolveRequest(),
                user=_user(),
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "bad obsolete mode"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_bom_substitute_remove_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.return_value = SimpleNamespace(
        id="line-1",
        item_type_id="Part BOM",
        source_id=None,
    )

    class FailingSubstituteService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def remove_substitute(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("substitute missing")

    monkeypatch.setattr(bom_substitutes_router, "MetaPermissionService", AllowAllPermissions)
    monkeypatch.setattr(bom_substitutes_router, "SubstituteService", FailingSubstituteService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            bom_substitutes_router.remove_bom_substitute(
                "line-1",
                "sub-1",
                user=_user(),
                db=db,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "substitute missing"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_not_called()
    db.commit.assert_not_called()


def test_bom_compare_version_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    version = SimpleNamespace(item_id="item-1")
    item = SimpleNamespace(id="item-1", item_type_id="Part")

    def get_model(_model: object, item_id: str) -> object:
        return version if item_id == "version-1" else item

    class FailingBOMService:
        @staticmethod
        def resolve_compare_mode(_compare_mode: object) -> tuple[None, None, bool]:
            return None, None, False

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def get_bom_for_version(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("version tree missing")

    db.get.side_effect = get_model
    monkeypatch.setattr(bom_compare_router, "MetaPermissionService", AllowAllPermissions)
    monkeypatch.setattr(bom_compare_router, "BOMService", FailingBOMService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            bom_compare_router.compare_bom(
                left_type="version",
                left_id="version-1",
                right_type="item",
                right_id="item-2",
                max_levels=10,
                effective_at=None,
                include_child_fields=False,
                include_relationship_props=None,
                line_key="child_config",
                compare_mode=None,
                include_substitutes=False,
                include_effectivity=False,
                user=_user(),
                db=db,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "version tree missing"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_bom_router_exception_chaining_is_source_pinned() -> None:
    for filename, expected_lines in EXPECTED_LINES.items():
        source = _source(WEB_DIR / filename)
        for expected_line in expected_lines:
            assert expected_line in source


def test_bom_router_family_has_no_bare_stringified_exception_mappings() -> None:
    offenders: list[str] = []
    for path in sorted(WEB_DIR.glob("bom*_router.py")):
        source = _source(path)
        for line_no, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if (
                stripped.startswith("raise HTTPException(")
                and "detail=str(" in stripped
                and " from " not in stripped
            ):
                offenders.append(f"{path.name}:{line_no}:{stripped}")

    assert offenders == []


def test_bom_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_bom_router_exception_chaining_closeout.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
