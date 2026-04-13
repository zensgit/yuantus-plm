"""
Tests for EcoPermissionAdapter (P0-2).

Validates that the adapter:
1. Delegates to MetaPermissionService when ECO rules exist
2. Falls back to allow when no ECO rules are configured
3. Passes the ECO state to the underlying permission check
4. Correctly maps each legacy action string to AMLAction
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from yuantus.meta_engine.services.eco_permission_adapter import (
    EcoPermissionAdapter,
    ECO_ITEM_TYPE,
    _ACTION_MAP,
)
from yuantus.meta_engine.schemas.aml import AMLAction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def adapter(mock_session):
    with patch(
        "yuantus.meta_engine.services.eco_permission_adapter.MetaPermissionService"
    ) as MockMPS:
        instance = MockMPS.return_value
        instance.check_permission = MagicMock(return_value=True)
        adapter = EcoPermissionAdapter(mock_session)
        adapter._meta_service = instance
        yield adapter


# ---------------------------------------------------------------------------
# 1. Delegation to MetaPermissionService when rules exist
# ---------------------------------------------------------------------------

class TestDelegation:
    def test_delegates_when_eco_rules_exist(self, adapter, mock_session):
        # Simulate that ECO ItemType with permission_id exists
        mock_item_type = MagicMock()
        mock_item_type.permission_id = "perm-eco-001"
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )
        # No ECO record for resource_id
        mock_session.get.return_value = None

        result = adapter.check_permission(42, "update", "ECO", resource_id="eco-1")

        assert result is True
        adapter._meta_service.check_permission.assert_called_once()
        call_kwargs = adapter._meta_service.check_permission.call_args
        assert call_kwargs.kwargs["item_type_id"] == ECO_ITEM_TYPE
        assert call_kwargs.kwargs["action"] == AMLAction.update

    def test_returns_false_when_meta_service_denies(self, adapter, mock_session):
        mock_item_type = MagicMock()
        mock_item_type.permission_id = "perm-eco-001"
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )
        mock_session.get.return_value = None
        adapter._meta_service.check_permission.return_value = False

        result = adapter.check_permission(42, "delete", "ECO", resource_id="eco-1")

        assert result is False


# ---------------------------------------------------------------------------
# 2. Fallback to allow when no ECO rules configured
# ---------------------------------------------------------------------------

class TestFallback:
    def test_allows_when_no_item_type(self, adapter, mock_session):
        # No ItemType row for ECO
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.get.return_value = None

        result = adapter.check_permission(42, "create", "ECO")

        assert result is True
        adapter._meta_service.check_permission.assert_not_called()

    def test_allows_when_item_type_has_no_permission_id(self, adapter, mock_session):
        mock_item_type = MagicMock()
        mock_item_type.permission_id = None
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )
        mock_session.get.return_value = None

        result = adapter.check_permission(42, "update", "ECO", resource_id="eco-1")

        assert result is True
        adapter._meta_service.check_permission.assert_not_called()

    def test_non_eco_resource_always_allowed(self, adapter, mock_session):
        result = adapter.check_permission(42, "create", "ECOStage")

        assert result is True
        adapter._meta_service.check_permission.assert_not_called()


# ---------------------------------------------------------------------------
# 3. ECO state is passed to permission check
# ---------------------------------------------------------------------------

class TestStatePassthrough:
    def test_eco_state_forwarded(self, adapter, mock_session):
        # Setup ECO rules exist
        mock_item_type = MagicMock()
        mock_item_type.permission_id = "perm-eco-001"
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )

        # Setup ECO with a specific state
        mock_eco = MagicMock()
        mock_eco.state = "Progress"
        mock_eco.created_by = 10
        mock_session.get.return_value = mock_eco

        adapter.check_permission(42, "execute", "ECO", resource_id="eco-1", field="apply")

        call_kwargs = adapter._meta_service.check_permission.call_args.kwargs
        assert call_kwargs["item_state"] == "Progress"
        assert call_kwargs["item_owner_id"] == "10"

    def test_no_state_when_eco_not_found(self, adapter, mock_session):
        mock_item_type = MagicMock()
        mock_item_type.permission_id = "perm-eco-001"
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )
        mock_session.get.return_value = None

        adapter.check_permission(42, "update", "ECO", resource_id="eco-missing")

        call_kwargs = adapter._meta_service.check_permission.call_args.kwargs
        assert call_kwargs["item_state"] is None
        assert call_kwargs["item_owner_id"] is None


# ---------------------------------------------------------------------------
# 4. Action mapping (create / update / execute / delete)
# ---------------------------------------------------------------------------

class TestActionMapping:
    @pytest.mark.parametrize(
        "legacy_action, expected_aml",
        [
            ("create", AMLAction.add),
            ("update", AMLAction.update),
            ("execute", AMLAction.update),
            ("delete", AMLAction.delete),
        ],
    )
    def test_action_map(self, adapter, mock_session, legacy_action, expected_aml):
        mock_item_type = MagicMock()
        mock_item_type.permission_id = "perm-eco-001"
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )
        mock_session.get.return_value = None

        adapter.check_permission(42, legacy_action, "ECO")

        call_kwargs = adapter._meta_service.check_permission.call_args.kwargs
        assert call_kwargs["action"] == expected_aml

    def test_action_map_dict_complete(self):
        assert _ACTION_MAP == {
            "create": AMLAction.add,
            "update": AMLAction.update,
            "execute": AMLAction.update,
            "delete": AMLAction.delete,
        }
