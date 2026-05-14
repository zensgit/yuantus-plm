from __future__ import annotations

import asyncio
from importlib import import_module
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[4]
WEB_ROUTER = ROOT / "src/yuantus/meta_engine/web/locale_router.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_LOCALE_ROUTER_EXCEPTION_CHAINING_20260514.md"
)

LOCALE_WRITE_CASES = [
    (
        "LocaleService",
        "upsert_translation",
        "TranslationUpsertRequest",
        {
            "record_type": "item",
            "record_id": "item-1",
            "field_name": "name",
            "lang": "zh_CN",
            "translated_value": "螺栓",
        },
        "invalid translation",
    ),
    (
        "ReportLocaleService",
        "create_report_profile",
        "ReportProfileCreateRequest",
        {"name": "BOM Export ZH", "lang": "zh_CN"},
        "invalid report profile",
    ),
]


class FailingLocaleService:
    def __init__(self, db: object) -> None:
        self.db = db

    def upsert_translation(self, **_kwargs: object) -> object:
        raise ValueError("invalid translation")


class FailingReportLocaleService:
    def __init__(self, db: object) -> None:
        self.db = db

    def create_profile(self, **_kwargs: object) -> object:
        raise ValueError("invalid report profile")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    (
        "service_name",
        "handler_name",
        "request_name",
        "request_kwargs",
        "expected_detail",
    ),
    LOCALE_WRITE_CASES,
)
def test_locale_write_failures_preserve_original_exception_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
    service_name: str,
    handler_name: str,
    request_name: str,
    request_kwargs: dict[str, object],
    expected_detail: str,
) -> None:
    module = import_module("yuantus.meta_engine.web.locale_router")
    service_cls = (
        FailingLocaleService
        if service_name == "LocaleService"
        else FailingReportLocaleService
    )
    monkeypatch.setattr(module, service_name, service_cls)
    request = getattr(module, request_name)(**request_kwargs)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(getattr(module, handler_name)(request, user_id=1, db=db))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()


def test_locale_router_exception_chaining_is_source_pinned() -> None:
    source = _source(WEB_ROUTER)
    assert (
        source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
        == 2
    )
    assert "raise HTTPException(status_code=400, detail=str(exc))\n" not in source


def test_locale_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_locale_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
