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
    "docs/DEV_AND_VERIFICATION_MAINTENANCE_ROUTER_EXCEPTION_CHAINING_20260513.md"
)

MAINTENANCE_WRITE_CASES = [
    (
        "yuantus.meta_engine.web.maintenance_request_router",
        "create_maintenance_request",
        "MaintenanceRequestCreateRequest",
        {"name": "Fix spindle", "equipment_id": "eq-1"},
        "invalid maintenance request",
    ),
    (
        "yuantus.meta_engine.web.maintenance_request_router",
        "transition_maintenance_request",
        "MaintenanceRequestTransitionRequest",
        {"target_state": "completed"},
        "invalid maintenance transition",
    ),
    (
        "yuantus.meta_engine.web.maintenance_equipment_router",
        "update_equipment_status",
        "EquipmentStatusRequest",
        {"status": "offline"},
        "invalid equipment status",
    ),
]

SOURCE_EXPECTATIONS = {
    "maintenance_request_router.py": 2,
    "maintenance_equipment_router.py": 1,
}


class FailingMaintenanceService:
    def __init__(self, db: object) -> None:
        self.db = db

    def create_request(self, **_kwargs: object) -> object:
        raise ValueError("invalid maintenance request")

    def transition_request(self, *_args: object, **_kwargs: object) -> object:
        raise ValueError("invalid maintenance transition")

    def update_equipment_status(self, *_args: object, **_kwargs: object) -> object:
        raise ValueError("invalid equipment status")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("module_name", "handler_name", "request_name", "request_kwargs", "expected_detail"),
    MAINTENANCE_WRITE_CASES,
)
def test_maintenance_write_failures_preserve_original_exception_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    handler_name: str,
    request_name: str,
    request_kwargs: dict[str, object],
    expected_detail: str,
) -> None:
    module = import_module(module_name)
    monkeypatch.setattr(module, "MaintenanceService", FailingMaintenanceService)
    request = getattr(module, request_name)(**request_kwargs)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        if handler_name == "create_maintenance_request":
            asyncio.run(getattr(module, handler_name)(request, user_id=1, db=db))
        else:
            asyncio.run(getattr(module, handler_name)("resource-1", request, db=db))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()


def test_maintenance_router_exception_chaining_is_source_pinned() -> None:
    for filename, expected_400_count in SOURCE_EXPECTATIONS.items():
        source = _source(WEB_DIR / filename)
        assert (
            source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
            == expected_400_count
        )
        assert "raise HTTPException(status_code=400, detail=str(exc))\n" not in source


def test_maintenance_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_maintenance_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
