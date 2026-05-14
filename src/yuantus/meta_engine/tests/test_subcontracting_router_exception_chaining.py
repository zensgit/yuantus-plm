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
    "docs/DEV_AND_VERIFICATION_SUBCONTRACTING_ROUTER_EXCEPTION_CHAINING_20260514.md"
)

ORDER_CASES = [
    (
        "create_order",
        "OrderCreateRequest",
        {"name": "Outside coating", "requested_qty": 5},
        400,
        "invalid subcontracting order",
        True,
    ),
    (
        "get_order",
        None,
        {},
        404,
        "subcontracting order not found",
        False,
    ),
    (
        "assign_vendor",
        "AssignVendorRequest",
        {"vendor_id": "vendor-1"},
        400,
        "invalid vendor assignment",
        True,
    ),
    (
        "issue_material",
        "QuantityEventRequest",
        {"quantity": 2},
        400,
        "invalid material issue",
        True,
    ),
    (
        "record_receipt",
        "QuantityEventRequest",
        {"quantity": 2},
        400,
        "invalid subcontracting receipt",
        True,
    ),
]

ANALYTICS_CASES = [
    (
        "export_subcontracting_overview",
        "overview export unavailable",
    ),
    (
        "export_subcontracting_vendors",
        "vendor export unavailable",
    ),
    (
        "export_subcontracting_receipts",
        "receipt export unavailable",
    ),
]

APPROVAL_MAPPING_CASES = [
    (
        "upsert_subcontracting_approval_role_mapping",
        "ApprovalRoleMappingRequest",
        {"role_code": "qa", "scope_type": "vendor"},
        "invalid approval role mapping",
        True,
    ),
    (
        "subcontracting_approval_role_mapping_registry",
        None,
        {},
        "invalid approval role mapping query",
        False,
    ),
    (
        "export_subcontracting_approval_role_mapping_registry",
        None,
        {},
        "approval role mapping export unavailable",
        False,
    ),
]

SOURCE_EXPECTATIONS = {
    "subcontracting_orders_router.py": (4, 1),
    "subcontracting_analytics_router.py": (3, 0),
    "subcontracting_approval_mapping_router.py": (3, 0),
}


class FailingSubcontractingService:
    def __init__(self, db: object) -> None:
        self.db = db

    def create_order(self, **_kwargs: object) -> object:
        raise ValueError("invalid subcontracting order")

    def get_order_read_model(self, _order_id: str) -> object:
        raise ValueError("subcontracting order not found")

    def assign_vendor(self, *_args: object, **_kwargs: object) -> object:
        raise ValueError("invalid vendor assignment")

    def record_material_issue(self, *_args: object, **_kwargs: object) -> object:
        raise ValueError("invalid material issue")

    def record_receipt(self, *_args: object, **_kwargs: object) -> object:
        raise ValueError("invalid subcontracting receipt")

    def export_overview(self, **_kwargs: object) -> object:
        raise ValueError("overview export unavailable")

    def export_vendor_analytics(self, **_kwargs: object) -> object:
        raise ValueError("vendor export unavailable")

    def export_receipt_analytics(self, **_kwargs: object) -> object:
        raise ValueError("receipt export unavailable")

    def upsert_approval_role_mapping(self, **_kwargs: object) -> object:
        raise ValueError("invalid approval role mapping")

    def get_approval_role_mapping_registry(self, **_kwargs: object) -> object:
        raise ValueError("invalid approval role mapping query")

    def export_approval_role_mapping_registry(self, **_kwargs: object) -> object:
        raise ValueError("approval role mapping export unavailable")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    (
        "handler_name",
        "request_name",
        "request_kwargs",
        "expected_status",
        "expected_detail",
        "expect_rollback",
    ),
    ORDER_CASES,
)
def test_subcontracting_order_failures_preserve_exception_and_rollback_contract(
    monkeypatch: pytest.MonkeyPatch,
    handler_name: str,
    request_name: str | None,
    request_kwargs: dict[str, object],
    expected_status: int,
    expected_detail: str,
    expect_rollback: bool,
) -> None:
    module = import_module("yuantus.meta_engine.web.subcontracting_orders_router")
    monkeypatch.setattr(module, "SubcontractingService", FailingSubcontractingService)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        if handler_name == "create_order":
            request = getattr(module, request_name)(**request_kwargs)
            asyncio.run(getattr(module, handler_name)(request, user_id=1, db=db))
        elif handler_name == "get_order":
            asyncio.run(getattr(module, handler_name)("order-1", db=db))
        else:
            request = getattr(module, request_name)(**request_kwargs)
            if handler_name in {"issue_material", "record_receipt"}:
                asyncio.run(
                    getattr(module, handler_name)("order-1", request, user_id=1, db=db)
                )
            else:
                asyncio.run(getattr(module, handler_name)("order-1", request, db=db))

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)
    if expect_rollback:
        db.rollback.assert_called_once_with()
    else:
        db.rollback.assert_not_called()


@pytest.mark.parametrize(("handler_name", "expected_detail"), ANALYTICS_CASES)
def test_subcontracting_analytics_export_failures_preserve_exception(
    monkeypatch: pytest.MonkeyPatch,
    handler_name: str,
    expected_detail: str,
) -> None:
    module = import_module("yuantus.meta_engine.web.subcontracting_analytics_router")
    monkeypatch.setattr(module, "SubcontractingService", FailingSubcontractingService)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(getattr(module, handler_name)(format="json", db=db))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_not_called()


@pytest.mark.parametrize(
    ("handler_name", "request_name", "request_kwargs", "expected_detail", "expect_rollback"),
    APPROVAL_MAPPING_CASES,
)
def test_subcontracting_approval_mapping_failures_preserve_exception_and_rollback_contract(
    monkeypatch: pytest.MonkeyPatch,
    handler_name: str,
    request_name: str | None,
    request_kwargs: dict[str, object],
    expected_detail: str,
    expect_rollback: bool,
) -> None:
    module = import_module(
        "yuantus.meta_engine.web.subcontracting_approval_mapping_router"
    )
    monkeypatch.setattr(module, "SubcontractingService", FailingSubcontractingService)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        if request_name is not None:
            request = getattr(module, request_name)(**request_kwargs)
            asyncio.run(getattr(module, handler_name)(request, user_id=1, db=db))
        elif handler_name == "export_subcontracting_approval_role_mapping_registry":
            asyncio.run(getattr(module, handler_name)(format="json", db=db))
        else:
            asyncio.run(getattr(module, handler_name)(db=db))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)
    if expect_rollback:
        db.rollback.assert_called_once_with()
    else:
        db.rollback.assert_not_called()


def test_subcontracting_router_exception_chaining_is_source_pinned() -> None:
    for filename, (expected_400_count, expected_404_count) in SOURCE_EXPECTATIONS.items():
        source = _source(WEB_DIR / filename)
        assert (
            source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
            == expected_400_count
        )
        assert (
            source.count("raise HTTPException(status_code=404, detail=str(exc)) from exc")
            == expected_404_count
        )
        assert "raise HTTPException(status_code=400, detail=str(exc))\n" not in source
        assert "raise HTTPException(status_code=404, detail=str(exc))\n" not in source


def test_subcontracting_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_subcontracting_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
