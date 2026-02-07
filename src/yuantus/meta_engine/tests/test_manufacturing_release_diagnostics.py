import json
from unittest.mock import MagicMock

import pytest

from yuantus.config.settings import get_settings
from yuantus.meta_engine.manufacturing.mbom_service import MBOMService
from yuantus.meta_engine.manufacturing.models import ManufacturingBOM, Operation, Routing, WorkCenter
from yuantus.meta_engine.manufacturing.routing_service import RoutingService


def test_routing_release_diagnostics_collects_multiple_issues():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1", version="1.0", state="draft")
    session.get.side_effect = lambda model, key: routing if model == Routing else None

    service = RoutingService(session)
    service.list_operations = MagicMock(return_value=[])

    diagnostics = service.get_release_diagnostics("routing-1", ruleset_id="default")

    codes = [issue.code for issue in diagnostics["errors"]]
    assert "routing_empty_operations" in codes
    assert "routing_missing_scope" in codes


def test_routing_release_diagnostics_reports_workcenter_issues_per_operation():
    session = MagicMock()
    routing = Routing(
        id="routing-1",
        item_id="item-1",
        name="R1",
        version="1.0",
        state="draft",
        plant_code="P1",
        line_code="L1",
    )

    op_missing = Operation(
        id="op-1",
        routing_id="routing-1",
        operation_number="10",
        name="Cut",
        workcenter_id="wc-missing",
        workcenter_code=None,
    )
    op_inactive = Operation(
        id="op-2",
        routing_id="routing-1",
        operation_number="20",
        name="Weld",
        workcenter_id="wc-inactive",
        workcenter_code="WC-2",
    )

    inactive_wc = WorkCenter(
        id="wc-inactive",
        code="WC-2",
        name="WC2",
        is_active=False,
        plant_code="P1",
        department_code="L1",
    )

    def _get(model, key):
        if model == Routing and key == "routing-1":
            return routing
        if model == WorkCenter and key == "wc-inactive":
            return inactive_wc
        if model == WorkCenter and key == "wc-missing":
            return None
        return None

    session.get.side_effect = _get

    routing_query = MagicMock()
    routing_filtered = MagicMock()
    routing_filtered.count.return_value = 1
    routing_query.filter.return_value = routing_filtered
    session.query.side_effect = lambda model: routing_query

    service = RoutingService(session)
    service.list_operations = MagicMock(return_value=[op_missing, op_inactive])

    diagnostics = service.get_release_diagnostics("routing-1", ruleset_id="default")
    codes = [issue.code for issue in diagnostics["errors"]]
    assert "workcenter_not_found" in codes
    assert "workcenter_inactive" in codes


def test_routing_release_ruleset_can_skip_primary_check(monkeypatch):
    monkeypatch.setenv(
        "YUANTUS_RELEASE_VALIDATION_RULESETS_JSON",
        json.dumps(
            {
                "routing_release": {
                    "no_primary": [
                        "routing.exists",
                        "routing.not_already_released",
                        "routing.has_operations",
                        "routing.has_scope",
                        "routing.operation_workcenters_valid",
                    ]
                }
            }
        ),
    )
    get_settings.cache_clear()

    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", version="1.0", state="draft")
    session.get.side_effect = lambda model, key: routing if model == Routing else None

    service = RoutingService(session)
    service.list_operations = MagicMock(
        return_value=[Operation(id="op-1", routing_id="routing-1", operation_number="10", name="Cut")]
    )

    diagnostics = service.get_release_diagnostics("routing-1", ruleset_id="no_primary")
    assert diagnostics["errors"] == []

    released = service.release_routing("routing-1", ruleset_id="no_primary")
    assert released.state == "released"
    assert not session.query.called

    get_settings.cache_clear()


def test_mbom_release_diagnostics_collects_multiple_issues():
    session = MagicMock()
    mbom = ManufacturingBOM(
        id="mbom-1",
        source_item_id="item-1",
        name="MBOM 1",
        version="1.0",
        state="draft",
        structure={},
    )
    session.get.side_effect = lambda model, key: mbom if model == ManufacturingBOM else None

    routing_query = MagicMock()
    routing_filtered = MagicMock()
    routing_filtered.count.return_value = 0
    routing_query.filter.return_value = routing_filtered
    session.query.side_effect = lambda model: routing_query

    service = MBOMService(session)
    diagnostics = service.get_release_diagnostics("mbom-1", ruleset_id="default")
    codes = [issue.code for issue in diagnostics["errors"]]
    assert "mbom_empty_structure" in codes
    assert "mbom_missing_released_routing" in codes

