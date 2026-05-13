from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import approval_request_router as approval_request_module


ROOT = Path(__file__).resolve().parents[4]
APPROVAL_REQUEST_ROUTER = ROOT / "src/yuantus/meta_engine/web/approval_request_router.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_APPROVAL_REQUEST_ROUTER_EXCEPTION_CHAINING_20260512.md"
)


class FailingApprovalService:
    def __init__(self, db: object) -> None:
        self.db = db

    def export_requests(self, **_: object) -> object:
        raise ValueError("request export invalid")

    def get_request_lifecycle(self, request_id: str) -> object:
        raise ValueError(f"request not found: {request_id}")

    def get_request_consumer_summary(self, request_id: str, **_: object) -> object:
        raise ValueError(f"summary not found: {request_id}")

    def get_request_history(self, request_id: str, **_: object) -> object:
        raise ValueError(f"history not found: {request_id}")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_http_exception_preserves_value_error(
    coro: object,
    *,
    status_code: int,
    detail: str,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(coro)

    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_export_requests_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_request_module, "ApprovalService", FailingApprovalService)

    _assert_http_exception_preserves_value_error(
        approval_request_module.export_approval_requests(
            format="json",
            state=None,
            category_id=None,
            entity_type=None,
            entity_id=None,
            priority=None,
            assigned_to_id=None,
            db=MagicMock(),
        ),
        status_code=400,
        detail="request export invalid",
    )


def test_request_lifecycle_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_request_module, "ApprovalService", FailingApprovalService)

    _assert_http_exception_preserves_value_error(
        approval_request_module.get_approval_request_lifecycle(
            request_id="req-1",
            db=MagicMock(),
        ),
        status_code=404,
        detail="request not found: req-1",
    )


def test_consumer_summary_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_request_module, "ApprovalService", FailingApprovalService)

    _assert_http_exception_preserves_value_error(
        approval_request_module.get_approval_request_consumer_summary(
            request_id="req-1",
            include_history=False,
            history_limit=5,
            db=MagicMock(),
        ),
        status_code=404,
        detail="summary not found: req-1",
    )


def test_request_history_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_request_module, "ApprovalService", FailingApprovalService)

    _assert_http_exception_preserves_value_error(
        approval_request_module.get_approval_request_history(
            request_id="req-1",
            history_limit=5,
            db=MagicMock(),
        ),
        status_code=404,
        detail="history not found: req-1",
    )


def test_approval_request_router_exception_chaining_is_source_pinned() -> None:
    source = _source(APPROVAL_REQUEST_ROUTER)

    assert (
        source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
        == 1
    )
    assert (
        source.count("raise HTTPException(status_code=404, detail=str(exc)) from exc")
        == 3
    )


def test_approval_request_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_approval_request_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
