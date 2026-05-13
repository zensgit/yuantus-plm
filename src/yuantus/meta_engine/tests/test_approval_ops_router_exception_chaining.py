from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import approval_ops_router as approval_ops_module


ROOT = Path(__file__).resolve().parents[4]
APPROVAL_OPS_ROUTER = ROOT / "src/yuantus/meta_engine/web/approval_ops_router.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_APPROVAL_OPS_ROUTER_EXCEPTION_CHAINING_20260512.md"
)


class FailingApprovalService:
    def __init__(self, db: object) -> None:
        self.db = db

    def export_summary(self, **_: object) -> object:
        raise ValueError("summary export invalid")

    def export_ops_report(self, **_: object) -> object:
        raise ValueError("ops report export invalid")

    def get_queue_health(self, **_: object) -> object:
        raise ValueError("queue health invalid")

    def export_queue_health(self, **_: object) -> object:
        raise ValueError("queue health export invalid")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_bad_request_preserves_value_error(coro: object, detail: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(coro)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == detail
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_export_summary_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_ops_module, "ApprovalService", FailingApprovalService)

    _assert_bad_request_preserves_value_error(
        approval_ops_module.export_approval_summary(
            format="json",
            entity_type=None,
            category_id=None,
            db=MagicMock(),
        ),
        "summary export invalid",
    )


def test_export_ops_report_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_ops_module, "ApprovalService", FailingApprovalService)

    _assert_bad_request_preserves_value_error(
        approval_ops_module.export_approvals_ops_report(format="json", db=MagicMock()),
        "ops report export invalid",
    )


def test_queue_health_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_ops_module, "ApprovalService", FailingApprovalService)

    _assert_bad_request_preserves_value_error(
        approval_ops_module.approvals_queue_health(
            stale_after_hours=24,
            warn_after_hours=4,
            entity_type=None,
            category_id=None,
            db=MagicMock(),
        ),
        "queue health invalid",
    )


def test_export_queue_health_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(approval_ops_module, "ApprovalService", FailingApprovalService)

    _assert_bad_request_preserves_value_error(
        approval_ops_module.export_approvals_queue_health(
            format="json",
            stale_after_hours=24,
            warn_after_hours=4,
            entity_type=None,
            category_id=None,
            db=MagicMock(),
        ),
        "queue health export invalid",
    )


def test_approval_ops_router_exception_chaining_is_source_pinned() -> None:
    source = _source(APPROVAL_OPS_ROUTER)

    assert (
        source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
        == 4
    )


def test_approval_ops_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_approval_ops_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
