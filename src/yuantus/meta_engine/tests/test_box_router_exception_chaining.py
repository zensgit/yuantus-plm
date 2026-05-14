from __future__ import annotations

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
    "docs/DEV_AND_VERIFICATION_BOX_ROUTER_EXCEPTION_CHAINING_20260513.md"
)

BOX_ID_CASES = [
    (
        "yuantus.meta_engine.web.box_aging_router",
        "box_item_aging",
        "box aging not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_analytics_router",
        "box_contents_summary",
        "contents summary not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_analytics_router",
        "box_export_contents",
        "export contents not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_capacity_router",
        "box_item_capacity",
        "box capacity not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_core_router",
        "export_box_meta",
        "box meta not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_custody_router",
        "box_item_custody",
        "box custody not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_ops_router",
        "box_ops_report",
        "ops report not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_policy_router",
        "box_policy_check",
        "policy check not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_reconciliation_router",
        "box_item_reconciliation",
        "box reconciliation not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_traceability_router",
        "box_item_reservations",
        "box reservations not found: box-1",
    ),
    (
        "yuantus.meta_engine.web.box_turnover_router",
        "box_item_turnover",
        "box turnover not found: box-1",
    ),
]

SOURCE_EXPECTATIONS = {
    "box_aging_router.py": (0, 1),
    "box_analytics_router.py": (0, 2),
    "box_capacity_router.py": (0, 1),
    "box_core_router.py": (1, 1),
    "box_custody_router.py": (0, 1),
    "box_ops_router.py": (0, 1),
    "box_policy_router.py": (0, 1),
    "box_reconciliation_router.py": (0, 1),
    "box_traceability_router.py": (0, 1),
    "box_turnover_router.py": (0, 1),
}


class FailingBoxService:
    def __init__(self, db: object) -> None:
        self.db = db

    def create_box(self, **_kwargs: object) -> object:
        raise ValueError("invalid box request")

    def box_aging(self, box_id: str) -> object:
        raise ValueError(f"box aging not found: {box_id}")

    def contents_summary(self, box_id: str) -> object:
        raise ValueError(f"contents summary not found: {box_id}")

    def export_contents(self, box_id: str) -> object:
        raise ValueError(f"export contents not found: {box_id}")

    def box_capacity(self, box_id: str) -> object:
        raise ValueError(f"box capacity not found: {box_id}")

    def export_meta(self, box_id: str) -> object:
        raise ValueError(f"box meta not found: {box_id}")

    def box_custody(self, box_id: str) -> object:
        raise ValueError(f"box custody not found: {box_id}")

    def ops_report(self, box_id: str) -> object:
        raise ValueError(f"ops report not found: {box_id}")

    def box_policy_check(self, box_id: str) -> object:
        raise ValueError(f"policy check not found: {box_id}")

    def box_reconciliation(self, box_id: str) -> object:
        raise ValueError(f"box reconciliation not found: {box_id}")

    def box_reservations(self, box_id: str) -> object:
        raise ValueError(f"box reservations not found: {box_id}")

    def box_turnover(self, box_id: str) -> object:
        raise ValueError(f"box turnover not found: {box_id}")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    return user


@pytest.mark.parametrize(("module_name", "handler_name", "expected_detail"), BOX_ID_CASES)
def test_box_lookup_failures_preserve_original_exception(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    handler_name: str,
    expected_detail: str,
) -> None:
    module = import_module(module_name)
    monkeypatch.setattr(module, "BoxService", FailingBoxService)

    with pytest.raises(HTTPException) as exc_info:
        getattr(module, handler_name)(
            box_id="box-1",
            db=MagicMock(),
            user=MagicMock(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_box_create_item_failure_preserves_original_exception_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("yuantus.meta_engine.web.box_core_router")
    monkeypatch.setattr(module, "BoxService", FailingBoxService)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        module.create_box_item(
            request=module.BoxCreateRequest(name="Box 1"),
            db=db,
            user=_user(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "invalid box request"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()


def test_box_router_exception_chaining_is_source_pinned() -> None:
    for filename, (expected_400, expected_404) in SOURCE_EXPECTATIONS.items():
        source = _source(WEB_DIR / filename)
        assert (
            source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
            == expected_400
        )
        assert (
            source.count("raise HTTPException(status_code=404, detail=str(exc)) from exc")
            == expected_404
        )
        assert "raise HTTPException(status_code=400, detail=str(exc))\n" not in source
        assert "raise HTTPException(status_code=404, detail=str(exc))\n" not in source


def test_box_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert "src/yuantus/meta_engine/tests/test_box_router_exception_chaining.py" in workflow
    assert DEV_VERIFICATION_DOC in index
