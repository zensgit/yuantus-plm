"""
Tests for ECO Routing Change tracking with rebase conflict detection (P0-3).

Covers:
- compute_routing_changes detects added/removed/updated operations
- routing conflict detection in rebase
- routing changes are stored as ECORoutingChange rows
- API endpoints return correct data
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.models.eco import ECORoutingChange


# ---- helpers ----


@pytest.fixture(autouse=True)
def _auth_optional(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _make_operation(
    op_id,
    routing_id="rt-1",
    operation_number=None,
    name="Op",
    workcenter_id="wc-1",
    setup_time=30.0,
    run_time=120.0,
    sequence=10,
    operation_type="assembly",
):
    """Return a lightweight Operation-like object for service tests."""
    op = SimpleNamespace(
        id=op_id,
        routing_id=routing_id,
        operation_number=operation_number or op_id,
        name=name,
        workcenter_id=workcenter_id,
        setup_time=setup_time,
        run_time=run_time,
        sequence=sequence,
        operation_type=operation_type,
    )
    return op


def _client():
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def override_user():
        return 1

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = override_user
    return TestClient(app), mock_db


# ---- Model tests ----


class TestECORoutingChangeModel:
    def test_to_dict_contains_expected_keys(self):
        rc = ECORoutingChange(
            id="rc-1",
            eco_id="eco-1",
            routing_id="rt-1",
            operation_id="op-1",
            change_type="add",
            old_snapshot=None,
            new_snapshot={"name": "Assembly", "setup_time": 30},
            conflict=False,
            conflict_reason=None,
        )
        d = rc.to_dict()
        assert d["id"] == "rc-1"
        assert d["eco_id"] == "eco-1"
        assert d["routing_id"] == "rt-1"
        assert d["operation_id"] == "op-1"
        assert d["change_type"] == "add"
        assert d["old_snapshot"] is None
        assert d["new_snapshot"]["name"] == "Assembly"
        assert d["conflict"] is False

    def test_to_dict_with_conflict(self):
        rc = ECORoutingChange(
            id="rc-2",
            eco_id="eco-1",
            routing_id=None,
            operation_id="op-1",
            change_type="update",
            old_snapshot={"setup_time": 30},
            new_snapshot={"setup_time": 60},
            conflict=True,
            conflict_reason="concurrent_routing_modification",
        )
        d = rc.to_dict()
        assert d["conflict"] is True
        assert d["conflict_reason"] == "concurrent_routing_modification"


# ---- Service tests ----


class TestComputeRoutingChanges:
    """Tests for ECOService.compute_routing_changes()."""

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_detect_added_operation(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        service.get_eco = MagicMock(return_value=eco)

        # Source has no ops; target has one new op
        new_op = _make_operation("op-new", name="Welding", operation_type="fabrication")
        service._get_operations_for_product_version = MagicMock(
            side_effect=lambda pid, vid: [] if vid == "v1" else [new_op]
        )

        # Mock the delete query
        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        result = service.compute_routing_changes("eco-1")

        assert len(result) == 1
        assert result[0]["change_type"] == "add"
        assert result[0]["operation_id"] == "op-new"
        assert result[0]["new_snapshot"]["name"] == "Welding"
        assert result[0]["old_snapshot"] is None

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_detect_removed_operation(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        service.get_eco = MagicMock(return_value=eco)

        old_op = _make_operation("op-old", name="Inspection")
        service._get_operations_for_product_version = MagicMock(
            side_effect=lambda pid, vid: [old_op] if vid == "v1" else []
        )

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        result = service.compute_routing_changes("eco-1")

        assert len(result) == 1
        assert result[0]["change_type"] == "remove"
        assert result[0]["operation_id"] == "op-old"
        assert result[0]["old_snapshot"]["name"] == "Inspection"
        assert result[0]["new_snapshot"] is None

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_detect_updated_operation(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        service.get_eco = MagicMock(return_value=eco)

        old_op = _make_operation("op-1", setup_time=30.0, run_time=120.0)
        new_op = _make_operation("op-1", setup_time=45.0, run_time=90.0)

        service._get_operations_for_product_version = MagicMock(
            side_effect=lambda pid, vid: [old_op] if vid == "v1" else [new_op]
        )

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        result = service.compute_routing_changes("eco-1")

        assert len(result) == 1
        assert result[0]["change_type"] == "update"
        assert result[0]["old_snapshot"]["setup_time"] == 30.0
        assert result[0]["new_snapshot"]["setup_time"] == 45.0
        assert result[0]["old_snapshot"]["run_time"] == 120.0
        assert result[0]["new_snapshot"]["run_time"] == 90.0

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_detect_updated_cloned_operation(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        service.get_eco = MagicMock(return_value=eco)

        source_op = _make_operation(
            "source-op-1",
            operation_number="10",
            setup_time=30.0,
            run_time=120.0,
        )
        cloned_op = _make_operation(
            "target-op-9",
            operation_number="10",
            setup_time=45.0,
            run_time=90.0,
        )

        service._get_operations_for_product_version = MagicMock(
            side_effect=lambda pid, vid: [source_op] if vid == "v1" else [cloned_op]
        )

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        result = service.compute_routing_changes("eco-1")

        assert len(result) == 1
        assert result[0]["change_type"] == "update"
        assert result[0]["operation_id"] == "target-op-9"
        assert result[0]["old_snapshot"]["setup_time"] == 30.0
        assert result[0]["new_snapshot"]["setup_time"] == 45.0

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_no_changes_when_identical(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        service.get_eco = MagicMock(return_value=eco)

        op = _make_operation("op-1")
        service._get_operations_for_product_version = MagicMock(return_value=[op])

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        result = service.compute_routing_changes("eco-1")
        assert len(result) == 0

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_raises_when_eco_not_found(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)
        service.get_eco = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            service.compute_routing_changes("eco-missing")

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_changes_stored_as_routing_change_rows(self, _MockOp, _MockRouting):
        """Verify that session.add is called for each change."""
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        service.get_eco = MagicMock(return_value=eco)

        op_add = _make_operation("op-add", name="New Op")
        op_remove = _make_operation("op-remove", name="Old Op")

        service._get_operations_for_product_version = MagicMock(
            side_effect=lambda pid, vid: [op_remove] if vid == "v1" else [op_add]
        )

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        result = service.compute_routing_changes("eco-1")

        # 2 changes: 1 add + 1 remove
        assert len(result) == 2
        # session.add called for each change
        assert session.add.call_count == 2


# ---- Rebase conflict tests ----


class TestRoutingRebaseConflicts:
    """Tests for routing conflict detection in rebase."""

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_no_routing_conflict_when_no_rebase_needed(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)
        service.check_rebase_needed = MagicMock(return_value=False)

        conflicts = service.detect_rebase_conflicts("eco-1")
        assert conflicts == []

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_routing_conflict_detected(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        product = SimpleNamespace(
            id="prod-1",
            current_version_id="v3",
        )

        service.check_rebase_needed = MagicMock(return_value=True)
        service.get_eco = MagicMock(return_value=eco)
        session.get = MagicMock(return_value=product)
        session.refresh = MagicMock()

        # Mock BOM side to return empty (no BOM conflicts)
        service.bom_service = MagicMock()
        service.bom_service.get_bom_for_version.return_value = {"children": []}

        # Base op: setup_time=30
        base_op = _make_operation("op-1", setup_time=30.0)
        # My op: setup_time=60 (I changed it)
        my_op = _make_operation("op-1", setup_time=60.0)
        # Theirs op: setup_time=45 (they changed it differently)
        theirs_op = _make_operation("op-1", setup_time=45.0)

        def _get_ops(pid, vid):
            if vid == "v1":
                return [base_op]
            elif vid == "v2":
                return [my_op]
            elif vid == "v3":
                return [theirs_op]
            return []

        service._get_operations_for_product_version = MagicMock(side_effect=_get_ops)

        conflicts = service.detect_rebase_conflicts("eco-1")

        routing_conflicts = [c for c in conflicts if c.get("type") == "routing"]
        assert len(routing_conflicts) == 1
        assert routing_conflicts[0]["operation_id"] == "op-1"
        assert routing_conflicts[0]["reason"] == "concurrent_routing_modification"

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_cloned_operation_rebase_matches_as_one_conflict(self, _MockOp, _MockRouting):
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        product = SimpleNamespace(
            id="prod-1",
            current_version_id="v3",
        )

        service.check_rebase_needed = MagicMock(return_value=True)
        service.get_eco = MagicMock(return_value=eco)
        session.get = MagicMock(return_value=product)
        session.refresh = MagicMock()

        service.bom_service = MagicMock()
        service.bom_service.get_bom_for_version.return_value = {"children": []}

        base_op = _make_operation(
            "base-op-1",
            operation_number="10",
            setup_time=30.0,
        )
        my_op = _make_operation(
            "my-op-7",
            operation_number="10",
            setup_time=60.0,
        )
        theirs_op = _make_operation(
            "their-op-4",
            operation_number="10",
            setup_time=45.0,
        )

        def _get_ops(pid, vid):
            if vid == "v1":
                return [base_op]
            if vid == "v2":
                return [my_op]
            if vid == "v3":
                return [theirs_op]
            return []

        service._get_operations_for_product_version = MagicMock(side_effect=_get_ops)

        conflicts = service.detect_rebase_conflicts("eco-1")

        routing_conflicts = [c for c in conflicts if c.get("type") == "routing"]
        assert len(routing_conflicts) == 1
        assert routing_conflicts[0]["operation_id"] == "my-op-7"

        added_objects = [call.args[0] for call in session.add.call_args_list]
        conflict_rows = [
            obj
            for obj in added_objects
            if isinstance(obj, ECORoutingChange) and obj.conflict is True
        ]
        assert len(conflict_rows) == 1
        assert conflict_rows[0].operation_id == "my-op-7"

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_no_conflict_when_same_change(self, _MockOp, _MockRouting):
        """Both branches made the same change -- should auto-merge, no conflict."""
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        product = SimpleNamespace(id="prod-1", current_version_id="v3")

        service.check_rebase_needed = MagicMock(return_value=True)
        service.get_eco = MagicMock(return_value=eco)
        session.get = MagicMock(return_value=product)
        session.refresh = MagicMock()

        service.bom_service = MagicMock()
        service.bom_service.get_bom_for_version.return_value = {"children": []}

        base_op = _make_operation("op-1", setup_time=30.0)
        same_op = _make_operation("op-1", setup_time=60.0)

        def _get_ops(pid, vid):
            if vid == "v1":
                return [base_op]
            return [same_op]  # Both v2 and v3 have the same change

        service._get_operations_for_product_version = MagicMock(side_effect=_get_ops)

        conflicts = service.detect_rebase_conflicts("eco-1")

        routing_conflicts = [c for c in conflicts if c.get("type") == "routing"]
        assert len(routing_conflicts) == 0

    @patch("yuantus.meta_engine.services.eco_service.Routing")
    @patch("yuantus.meta_engine.services.eco_service.Operation")
    def test_conflict_stores_routing_change_row(self, _MockOp, _MockRouting):
        """Routing conflicts should be stored as ECORoutingChange rows with conflict=True."""
        from yuantus.meta_engine.services.eco_service import ECOService

        session = MagicMock()
        service = ECOService(session)

        eco = SimpleNamespace(
            id="eco-1",
            product_id="prod-1",
            source_version_id="v1",
            target_version_id="v2",
        )
        product = SimpleNamespace(id="prod-1", current_version_id="v3")

        service.check_rebase_needed = MagicMock(return_value=True)
        service.get_eco = MagicMock(return_value=eco)
        session.get = MagicMock(return_value=product)
        session.refresh = MagicMock()

        service.bom_service = MagicMock()
        service.bom_service.get_bom_for_version.return_value = {"children": []}

        base_op = _make_operation("op-1", run_time=100.0)
        my_op = _make_operation("op-1", run_time=200.0)
        theirs_op = _make_operation("op-1", run_time=150.0)

        def _get_ops(pid, vid):
            if vid == "v1":
                return [base_op]
            elif vid == "v2":
                return [my_op]
            return [theirs_op]

        service._get_operations_for_product_version = MagicMock(side_effect=_get_ops)

        service.detect_rebase_conflicts("eco-1")

        # Verify session.add was called with a conflict routing change
        added_objects = [call.args[0] for call in session.add.call_args_list]
        conflict_rows = [
            obj
            for obj in added_objects
            if isinstance(obj, ECORoutingChange) and obj.conflict is True
        ]
        assert len(conflict_rows) == 1
        assert conflict_rows[0].conflict_reason == "concurrent_routing_modification"


# ---- Router / API tests ----


class TestECORoutingChangeRouter:
    def test_get_routing_changes_404_when_eco_missing(self):
        client, _db = _client()
        with patch(
            "yuantus.meta_engine.web.eco_change_analysis_router.ECOService"
        ) as svc_cls:
            svc_cls.return_value.get_eco.return_value = None
            resp = client.get("/api/v1/eco/eco-404/routing-changes")
        assert resp.status_code == 404

    def test_get_routing_changes_returns_list(self):
        client, _db = _client()
        mock_change = MagicMock()
        mock_change.to_dict.return_value = {
            "id": "rc-1",
            "eco_id": "eco-1",
            "change_type": "add",
            "routing_id": "rt-1",
            "operation_id": "op-1",
            "old_snapshot": None,
            "new_snapshot": {"name": "Assembly"},
            "conflict": False,
            "conflict_reason": None,
            "created_at": None,
        }
        with patch(
            "yuantus.meta_engine.web.eco_change_analysis_router.ECOService"
        ) as svc_cls:
            svc = svc_cls.return_value
            svc.get_eco.return_value = SimpleNamespace(id="eco-1")
            svc.get_routing_changes.return_value = [mock_change]
            resp = client.get("/api/v1/eco/eco-1/routing-changes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["change_type"] == "add"
        assert data[0]["operation_id"] == "op-1"

    def test_compute_routing_changes_returns_list(self):
        client, _db = _client()
        with patch(
            "yuantus.meta_engine.web.eco_change_analysis_router.ECOService"
        ) as svc_cls:
            svc = svc_cls.return_value
            svc.compute_routing_changes.return_value = [
                {
                    "id": "rc-1",
                    "eco_id": "eco-1",
                    "change_type": "update",
                    "routing_id": "rt-1",
                    "operation_id": "op-1",
                    "old_snapshot": {"setup_time": 30},
                    "new_snapshot": {"setup_time": 60},
                    "conflict": False,
                    "conflict_reason": None,
                    "created_at": None,
                }
            ]
            resp = client.post("/api/v1/eco/eco-1/compute-routing-changes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["change_type"] == "update"

    def test_compute_routing_changes_400_on_value_error(self):
        client, _db = _client()
        with patch(
            "yuantus.meta_engine.web.eco_change_analysis_router.ECOService"
        ) as svc_cls:
            svc = svc_cls.return_value
            svc.compute_routing_changes.side_effect = ValueError("ECO missing product")
            resp = client.post("/api/v1/eco/eco-1/compute-routing-changes")
        assert resp.status_code == 400
        assert "ECO missing product" in resp.json()["detail"]
