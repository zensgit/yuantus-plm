from __future__ import annotations

import asyncio
from importlib import import_module
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_QUALITY_ROUTER_EXCEPTION_CHAINING_20260513.md"
)

QUALITY_WRITE_CASES = [
    (
        "yuantus.meta_engine.web.quality_points_router",
        "create_quality_point",
        "QualityPointCreateRequest",
        {"name": "Point 1"},
        "invalid quality point request",
    ),
    (
        "yuantus.meta_engine.web.quality_checks_router",
        "create_quality_check",
        "QualityCheckCreateRequest",
        {"point_id": "point-1"},
        "invalid quality check request",
    ),
    (
        "yuantus.meta_engine.web.quality_checks_router",
        "record_quality_check",
        "QualityCheckRecordRequest",
        {"result": "pass"},
        "invalid quality check result",
    ),
    (
        "yuantus.meta_engine.web.quality_alerts_router",
        "create_quality_alert",
        "QualityAlertCreateRequest",
        {"name": "Alert 1"},
        "invalid quality alert request",
    ),
    (
        "yuantus.meta_engine.web.quality_alerts_router",
        "transition_quality_alert",
        "QualityAlertTransitionRequest",
        {"target_state": "resolved"},
        "invalid quality alert transition",
    ),
]

SOURCE_EXPECTATIONS = {
    "quality_alerts_router.py": 2,
    "quality_checks_router.py": 2,
    "quality_points_router.py": 1,
}


class FailingQualityService:
    def __init__(self, db: object) -> None:
        self.db = db

    def create_point(self, **_kwargs: object) -> object:
        raise ValueError("invalid quality point request")

    def create_check(self, **_kwargs: object) -> object:
        raise ValueError("invalid quality check request")

    def record_check_result(self, *_args: object, **_kwargs: object) -> object:
        raise ValueError("invalid quality check result")

    def create_alert(self, **_kwargs: object) -> object:
        raise ValueError("invalid quality alert request")

    def transition_alert(self, *_args: object, **_kwargs: object) -> object:
        raise ValueError("invalid quality alert transition")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("module_name", "handler_name", "request_name", "request_kwargs", "expected_detail"),
    QUALITY_WRITE_CASES,
)
def test_quality_write_failures_preserve_original_exception_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    handler_name: str,
    request_name: str,
    request_kwargs: dict[str, object],
    expected_detail: str,
) -> None:
    module = import_module(module_name)
    monkeypatch.setattr(module, "QualityService", FailingQualityService)
    request = getattr(module, request_name)(**request_kwargs)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        if handler_name in {"record_quality_check", "transition_quality_alert"}:
            asyncio.run(
                getattr(module, handler_name)(
                    "resource-1",
                    request,
                    user_id=1,
                    db=db,
                )
            )
        elif handler_name == "create_quality_alert":
            asyncio.run(getattr(module, handler_name)(request, user_id=1, db=db))
        elif handler_name == "create_quality_point":
            asyncio.run(getattr(module, handler_name)(request, user_id=1, db=db))
        else:
            asyncio.run(getattr(module, handler_name)(request, db=db))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()


def test_quality_router_exception_chaining_is_source_pinned() -> None:
    for filename, expected_400_count in SOURCE_EXPECTATIONS.items():
        source = _source(WEB_DIR / filename)
        assert (
            source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
            == expected_400_count
        )
        assert "raise HTTPException(status_code=400, detail=str(exc))\n" not in source


def test_quality_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert "src/yuantus/meta_engine/tests/test_quality_router_exception_chaining.py" in workflow
    assert DEV_VERIFICATION_DOC in index
