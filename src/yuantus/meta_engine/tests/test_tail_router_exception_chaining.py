from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import bom_compare_router
from yuantus.meta_engine.web import product_router
from yuantus.meta_engine.web import router as meta_router_module
from yuantus.meta_engine.web import rpc_router


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_TAIL_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md"
)

SOURCE_EXPECTATIONS = {
    "router.py": "raise HTTPException(status_code=400, detail=str(exc)) from exc",
    "rpc_router.py": "raise HTTPException(status_code=500, detail=str(exc)) from exc",
    "product_router.py": "raise HTTPException(status_code=404, detail=str(exc)) from exc",
    "bom_compare_router.py": "raise HTTPException(status_code=400, detail=str(exc)) from exc",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_meta_apply_defensive_failure_preserves_exception_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingEngine:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def apply(self, _aml: object) -> object:
            raise RuntimeError("invalid aml")

    monkeypatch.setattr(meta_router_module, "AMLEngine", FailingEngine)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(meta_router_module.apply_item(aml=MagicMock(), db=db, current_user=None))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "invalid aml"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_rpc_dispatch_unexpected_failure_preserves_exception_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    def failing_handler(_engine: object, _args: list[object], _kwargs: dict[str, object]) -> object:
        raise RuntimeError("rpc boom")

    monkeypatch.setattr(rpc_router, "get_handler", lambda _model, _method: failing_handler)
    monkeypatch.setattr(rpc_router, "AMLEngine", lambda *_args, **_kwargs: object())

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            rpc_router.rpc_dispatch(
                {"model": "Part", "method": "explode", "args": [], "kwargs": {}},
                db=db,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "rpc boom"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_product_detail_not_found_preserves_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    user = SimpleNamespace(id=1, roles=["viewer"])

    class FailingProductDetailService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def get_detail(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("product missing")

    monkeypatch.setattr(product_router, "ProductDetailService", FailingProductDetailService)

    with pytest.raises(HTTPException) as exc_info:
        product_router.get_product_detail("prod-1", user=user, db=db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "product missing"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_not_called()
    db.commit.assert_not_called()


def test_bom_compare_mode_failure_preserves_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    user = SimpleNamespace(id=1, roles=["viewer"])

    def failing_resolve_compare_mode(_compare_mode: object) -> object:
        raise ValueError("unsupported compare mode")

    monkeypatch.setattr(
        bom_compare_router.BOMService,
        "resolve_compare_mode",
        staticmethod(failing_resolve_compare_mode),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            bom_compare_router.compare_bom(
                left_type="item",
                left_id="left-1",
                right_type="item",
                right_id="right-1",
                max_levels=10,
                effective_at=None,
                include_child_fields=False,
                include_relationship_props=None,
                line_key="child_config",
                compare_mode="bad",
                include_substitutes=False,
                include_effectivity=False,
                user=user,
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "unsupported compare mode"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_not_called()
    db.commit.assert_not_called()


def test_tail_router_exception_chaining_is_source_pinned() -> None:
    for filename, expected_line in SOURCE_EXPECTATIONS.items():
        source = _source(WEB_DIR / filename)
        assert expected_line in source


def test_meta_engine_web_has_no_bare_str_exc_http_exception_conversions() -> None:
    offenders: list[str] = []
    for path in sorted(WEB_DIR.glob("*.py")):
        source = _source(path)
        for line_no, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if (
                stripped.startswith("raise HTTPException(")
                and "detail=str(exc)" in stripped
                and " from exc" not in stripped
            ):
                offenders.append(f"{path.name}:{line_no}:{stripped}")

    assert offenders == []


def test_tail_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert "src/yuantus/meta_engine/tests/test_tail_router_exception_chaining.py" in workflow
    assert DEV_VERIFICATION_DOC in index
