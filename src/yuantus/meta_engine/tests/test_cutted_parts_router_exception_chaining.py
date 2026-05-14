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
    "docs/DEV_AND_VERIFICATION_CUTTED_PARTS_ROUTER_EXCEPTION_CHAINING_20260513.md"
)


PLAN_ID_CASES = [
    (
        "yuantus.meta_engine.web.cutted_parts_alerts_router",
        "plan_alerts",
        "plan alerts not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_analytics_router",
        "waste_summary",
        "waste summary not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_benchmark_router",
        "quote_summary",
        "quote summary not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_bottlenecks_router",
        "plan_bottlenecks",
        "plan bottlenecks not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_core_router",
        "get_plan_summary",
        "plan summary not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_scenarios_router",
        "scenario_summary",
        "scenario summary not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_thresholds_router",
        "plan_threshold_check",
        "threshold check not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_throughput_router",
        "plan_cadence",
        "plan cadence not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_utilization_router",
        "plan_cost_summary",
        "cost summary not found: plan-1",
    ),
    (
        "yuantus.meta_engine.web.cutted_parts_variance_router",
        "plan_recommendations",
        "recommendations not found: plan-1",
    ),
]

SOURCE_EXPECTATIONS = {
    "cutted_parts_alerts_router.py": (0, 1),
    "cutted_parts_analytics_router.py": (0, 1),
    "cutted_parts_benchmark_router.py": (0, 1),
    "cutted_parts_bottlenecks_router.py": (0, 1),
    "cutted_parts_core_router.py": (1, 1),
    "cutted_parts_scenarios_router.py": (0, 1),
    "cutted_parts_thresholds_router.py": (0, 1),
    "cutted_parts_throughput_router.py": (0, 1),
    "cutted_parts_utilization_router.py": (0, 1),
    "cutted_parts_variance_router.py": (0, 1),
}


class FailingCuttedPartsService:
    def __init__(self, db: object) -> None:
        self.db = db

    def create_plan(self, **_kwargs: object) -> object:
        raise ValueError("invalid cut plan request")

    def plan_alerts(self, plan_id: str) -> object:
        raise ValueError(f"plan alerts not found: {plan_id}")

    def waste_summary(self, plan_id: str) -> object:
        raise ValueError(f"waste summary not found: {plan_id}")

    def quote_summary(self, plan_id: str) -> object:
        raise ValueError(f"quote summary not found: {plan_id}")

    def plan_bottlenecks(self, plan_id: str) -> object:
        raise ValueError(f"plan bottlenecks not found: {plan_id}")

    def plan_summary(self, plan_id: str) -> object:
        raise ValueError(f"plan summary not found: {plan_id}")

    def scenario_summary(self, plan_id: str) -> object:
        raise ValueError(f"scenario summary not found: {plan_id}")

    def plan_threshold_check(self, plan_id: str) -> object:
        raise ValueError(f"threshold check not found: {plan_id}")

    def plan_cadence(self, plan_id: str) -> object:
        raise ValueError(f"plan cadence not found: {plan_id}")

    def plan_cost_summary(self, plan_id: str) -> object:
        raise ValueError(f"cost summary not found: {plan_id}")

    def plan_recommendations(self, plan_id: str) -> object:
        raise ValueError(f"recommendations not found: {plan_id}")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    return user


@pytest.mark.parametrize(("module_name", "handler_name", "expected_detail"), PLAN_ID_CASES)
def test_cutted_parts_plan_lookup_failures_preserve_original_exception(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    handler_name: str,
    expected_detail: str,
) -> None:
    module = import_module(module_name)
    monkeypatch.setattr(module, "CuttedPartsService", FailingCuttedPartsService)

    with pytest.raises(HTTPException) as exc_info:
        getattr(module, handler_name)(
            plan_id="plan-1",
            db=MagicMock(),
            user=MagicMock(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_cutted_parts_create_plan_failure_preserves_original_exception_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("yuantus.meta_engine.web.cutted_parts_core_router")
    monkeypatch.setattr(module, "CuttedPartsService", FailingCuttedPartsService)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        module.create_plan(
            request=module.PlanCreateRequest(name="Plan 1"),
            db=db,
            user=_user(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "invalid cut plan request"
    assert isinstance(exc_info.value.__cause__, ValueError)
    db.rollback.assert_called_once_with()


def test_cutted_parts_router_exception_chaining_is_source_pinned() -> None:
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


def test_cutted_parts_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_cutted_parts_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
