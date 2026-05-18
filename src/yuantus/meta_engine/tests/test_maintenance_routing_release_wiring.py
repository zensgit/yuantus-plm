import json
from unittest.mock import MagicMock, patch

import pytest

from yuantus.config.settings import get_settings
from yuantus.meta_engine.maintenance.models import (
    Equipment,
    EquipmentStatus,
    MaintenanceRequest,
    MaintenanceRequestState,
)
from yuantus.meta_engine.manufacturing.models import Operation, Routing, WorkCenter
from yuantus.meta_engine.manufacturing import routing_service as routing_module
from yuantus.meta_engine.manufacturing.routing_service import RoutingService
from yuantus.meta_engine.services.release_validation import (
    ROUTING_RELEASE_MAINTENANCE_READY_RULE,
    get_release_ruleset,
    get_release_validation_directory,
)


class _Query:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def all(self):
        return list(self.rows)


def _session_for_maintenance_rows(*, equipment_rows, request_rows):
    session = MagicMock()

    def _query(model):
        if model == Equipment:
            return _Query(equipment_rows)
        if model == MaintenanceRequest:
            return _Query(request_rows)
        raise AssertionError(f"unexpected query model: {model!r}")

    session.query.side_effect = _query
    return session


def test_workcenter_maintenance_assertion_resolves_rows_through_contracts():
    equipment = Equipment(
        id="eq-1",
        name="CNC",
        status=EquipmentStatus.OPERATIONAL.value,
        workcenter_id="wc-1",
    )
    request = MaintenanceRequest(
        id="mr-1",
        name="Bearing repair",
        equipment_id="eq-1",
        state=MaintenanceRequestState.SUBMITTED.value,
    )
    service = RoutingService(
        _session_for_maintenance_rows(
            equipment_rows=[equipment],
            request_rows=[request],
        )
    )

    with patch(
        "yuantus.meta_engine.manufacturing.routing_service."
        "resolve_workcenter_maintenance_descriptors",
        wraps=routing_module.resolve_workcenter_maintenance_descriptors,
    ) as resolver_spy, patch(
        "yuantus.meta_engine.manufacturing.routing_service."
        "assert_workcenter_ready",
        wraps=routing_module.assert_workcenter_ready,
    ) as assert_spy:
        with pytest.raises(ValueError, match="workcenter_blocked:"):
            service.assert_workcenter_maintenance_ready("wc-1")

    assert resolver_spy.called
    assert assert_spy.called


def test_draft_request_surfaces_but_does_not_block_release_wiring():
    equipment = Equipment(
        id="eq-1",
        name="CNC",
        status=EquipmentStatus.OPERATIONAL.value,
        workcenter_id="wc-1",
    )
    request = MaintenanceRequest(
        id="mr-1",
        name="Draft PM",
        equipment_id="eq-1",
        state=MaintenanceRequestState.DRAFT.value,
    )
    service = RoutingService(
        _session_for_maintenance_rows(
            equipment_rows=[equipment],
            request_rows=[request],
        )
    )

    descriptors = service.resolve_workcenter_maintenance_descriptors("wc-1")
    assert descriptors[0].active_request_state == MaintenanceRequestState.DRAFT.value
    assert service.assert_workcenter_maintenance_ready("wc-1") is None


def test_routing_release_default_ruleset_does_not_enable_maintenance_gate():
    assert (
        ROUTING_RELEASE_MAINTENANCE_READY_RULE
        not in get_release_ruleset("routing_release", "default")
    )
    assert (
        ROUTING_RELEASE_MAINTENANCE_READY_RULE
        in get_release_ruleset("routing_release", "maintenance_ready")
    )

    directory = get_release_validation_directory()
    routing_kind = next(
        kind for kind in directory["kinds"] if kind["kind"] == "routing_release"
    )
    assert ROUTING_RELEASE_MAINTENANCE_READY_RULE in routing_kind["allowed_rule_ids"]
    assert "maintenance_ready" in {
        ruleset["ruleset_id"] for ruleset in routing_kind["rulesets"]
    }


def test_release_diagnostics_maps_maintenance_blockage_to_distinct_issue(monkeypatch):
    monkeypatch.setenv(
        "YUANTUS_RELEASE_VALIDATION_RULESETS_JSON",
        json.dumps(
            {
                "routing_release": {
                    "maintenance_only": [ROUTING_RELEASE_MAINTENANCE_READY_RULE]
                }
            }
        ),
    )
    get_settings.cache_clear()

    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", state="draft")
    workcenter = WorkCenter(id="wc-1", code="WC-1", name="Cell", is_active=True)
    operation = Operation(
        id="op-1",
        routing_id="routing-1",
        operation_number="10",
        name="Cut",
        workcenter_id="wc-1",
        workcenter_code="WC-1",
    )

    def _get(model, key):
        if model == Routing:
            return routing
        if model == WorkCenter:
            return workcenter
        return None

    session.get.side_effect = _get

    service = RoutingService(session)
    service.list_operations = MagicMock(return_value=[operation])
    service.assert_workcenter_maintenance_ready = MagicMock(
        side_effect=ValueError(
            "workcenter_blocked: 'wc-1' is blocked by maintenance: "
            "1 equipment (ids=['eq-1'])"
        )
    )

    diagnostics = service.get_release_diagnostics(
        "routing-1",
        ruleset_id="maintenance_only",
    )

    assert [issue.code for issue in diagnostics["errors"]] == [
        "workcenter_maintenance_blocked"
    ]
    issue = diagnostics["errors"][0]
    assert issue.rule_id == ROUTING_RELEASE_MAINTENANCE_READY_RULE
    assert issue.details["operation_id"] == "op-1"

    get_settings.cache_clear()


def test_release_routing_raises_when_maintenance_ready_rule_fails(monkeypatch):
    monkeypatch.setenv(
        "YUANTUS_RELEASE_VALIDATION_RULESETS_JSON",
        json.dumps(
            {
                "routing_release": {
                    "maintenance_only": [ROUTING_RELEASE_MAINTENANCE_READY_RULE]
                }
            }
        ),
    )
    get_settings.cache_clear()

    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", state="draft")
    workcenter = WorkCenter(id="wc-1", code="WC-1", name="Cell", is_active=True)
    operation = Operation(
        id="op-1",
        routing_id="routing-1",
        operation_number="10",
        name="Cut",
        workcenter_id="wc-1",
    )

    def _get(model, key):
        if model == Routing:
            return routing
        if model == WorkCenter:
            return workcenter
        return None

    session.get.side_effect = _get

    service = RoutingService(session)
    service.list_operations = MagicMock(return_value=[operation])
    service.assert_workcenter_maintenance_ready = MagicMock(
        side_effect=ValueError(
            "workcenter_unknown: 'wc-1' has no maintenance descriptors"
        )
    )

    with pytest.raises(ValueError, match="workcenter_unknown:"):
        service.release_routing("routing-1", ruleset_id="maintenance_only")

    get_settings.cache_clear()
