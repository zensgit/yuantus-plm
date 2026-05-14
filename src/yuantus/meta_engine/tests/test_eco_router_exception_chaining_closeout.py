from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import eco_approval_workflow_router
from yuantus.meta_engine.web import eco_change_analysis_router
from yuantus.meta_engine.web import eco_core_router
from yuantus.meta_engine.web import eco_impact_apply_router
from yuantus.meta_engine.web import eco_lifecycle_router
from yuantus.meta_engine.web import eco_stage_router


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_ECO_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md"
)

EXPECTED_CHAINED_COUNTS = {
    "eco_approval_workflow_router.py": 6,
    "eco_change_analysis_router.py": 6,
    "eco_core_router.py": 6,
    "eco_impact_apply_router.py": 9,
    "eco_lifecycle_router.py": 8,
    "eco_stage_router.py": 5,
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_eco_stage_create_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingStageService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def create_stage(self, *_args: object, **_kwargs: object) -> object:
            raise RuntimeError("stage rejected")

    monkeypatch.setattr(eco_stage_router, "ECOStageService", FailingStageService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            eco_stage_router.create_stage(
                eco_stage_router.StageCreate(name="Review"),
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "stage rejected"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_eco_core_create_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingEcoService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def create_eco(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("bad ECO")

    monkeypatch.setattr(eco_core_router, "ECOService", FailingEcoService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            eco_core_router.create_eco(
                eco_core_router.ECOCreate(name="ECO-1"),
                user_id=7,
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "bad ECO"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_eco_change_compute_failure_preserves_exception_cause_without_new_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingEcoService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def compute_bom_changes(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("bad compare mode")

    monkeypatch.setattr(eco_change_analysis_router, "ECOService", FailingEcoService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(eco_change_analysis_router.compute_bom_changes("eco-1", db=db))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "bad compare mode"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_not_called()
    db.commit.assert_not_called()


def test_eco_impact_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    user = SimpleNamespace(id=7, roles=["engineer"])

    class FailingEcoService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def analyze_impact(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("impact unavailable")

    monkeypatch.setattr(eco_impact_apply_router, "ECOService", FailingEcoService)
    monkeypatch.setattr(
        eco_impact_apply_router,
        "_get_eco_product_or_404",
        lambda *_args, **_kwargs: (SimpleNamespace(id="eco-1"), SimpleNamespace(id="part-1")),
    )
    monkeypatch.setattr(
        eco_impact_apply_router,
        "_ensure_can_read_eco_product_bom",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            eco_impact_apply_router.get_eco_impact(
                "eco-1",
                include_files=False,
                include_bom_diff=False,
                include_version_diff=False,
                max_levels=10,
                effective_at=None,
                include_child_fields=False,
                include_relationship_props=None,
                compare_mode=None,
                user=user,
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "impact unavailable"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_eco_lifecycle_cancel_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingEcoService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def action_cancel(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("cannot cancel")

    monkeypatch.setattr(eco_lifecycle_router, "ECOService", FailingEcoService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            eco_lifecycle_router.cancel_eco(
                "eco-1",
                reason=None,
                user_id=7,
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "cannot cancel"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.commit.assert_not_called()


def test_eco_approval_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingApprovalService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def approve(self, *_args: object, **_kwargs: object) -> object:
            raise ValueError("approval rejected")

    monkeypatch.setattr(
        eco_approval_workflow_router,
        "ECOApprovalService",
        FailingApprovalService,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            eco_approval_workflow_router.approve_eco(
                "eco-1",
                eco_approval_workflow_router.ApprovalRequest(comment=None),
                user_id=7,
                db=db,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "approval rejected"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.commit.assert_not_called()


def test_eco_router_exception_chaining_is_source_pinned() -> None:
    for filename, expected_count in EXPECTED_CHAINED_COUNTS.items():
        source = _source(WEB_DIR / filename)
        assert (
            source.count("raise HTTPException(status_code=400, detail=str(e)) from e")
            + source.count("raise HTTPException(status_code=404, detail=str(e)) from e")
            + source.count("raise HTTPException(status_code=500, detail=str(e)) from e")
            + source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
        ) == expected_count


def test_eco_router_family_has_no_bare_stringified_exception_mappings() -> None:
    offenders: list[str] = []
    for path in sorted(WEB_DIR.glob("eco*_router.py")):
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


def test_eco_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    doc_index = _source(DOC_INDEX)

    assert "test_eco_router_exception_chaining_closeout.py" in workflow
    assert DEV_VERIFICATION_DOC in doc_index
    assert (ROOT / DEV_VERIFICATION_DOC).exists()
