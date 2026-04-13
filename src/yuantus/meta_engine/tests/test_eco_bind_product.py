"""
Tests for ECOService.bind_product() — the canonical product binding command.
PR-3 of PLM core convergence.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from yuantus.meta_engine.services.eco_service import ECOService
from yuantus.meta_engine.models.eco import ECO, ECOState
from yuantus.meta_engine.models.item import Item


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def eco_service(mock_session):
    with patch(
        "yuantus.meta_engine.services.eco_service.ECOService.__init__",
        lambda self, *a, **kw: None,
    ):
        svc = ECOService.__new__(ECOService)
        svc.session = mock_session
        svc.permission_service = MagicMock()
        svc.version_service = MagicMock()
        svc.audit_service = MagicMock()
        svc.notification_service = MagicMock()
        svc._event_queue = []
        return svc


def _make_eco(
    eco_id="eco-1",
    state=ECOState.DRAFT.value,
    product_id=None,
    target_version_id=None,
):
    eco = ECO(
        id=eco_id,
        name="Test ECO",
        eco_type="bom",
        state=state,
        product_id=product_id,
        target_version_id=target_version_id,
        created_by_id=1,
    )
    return eco


class TestBindProduct:
    def test_binds_once_and_is_idempotent(self, eco_service, mock_session):
        """Binding the same product twice returns the same ECO without error."""
        eco = _make_eco(product_id="prod-1")
        eco_service.get_eco = MagicMock(return_value=eco)

        result = eco_service.bind_product("eco-1", "prod-1", user_id=1)

        assert result.product_id == "prod-1"
        # Should NOT have called session.add (no change needed)
        eco_service.permission_service.check_permission.assert_called_once()

    def test_binds_product_when_unbound(self, eco_service, mock_session):
        """First binding sets product_id and emits event."""
        eco = _make_eco(product_id=None)
        eco_service.get_eco = MagicMock(return_value=eco)
        mock_session.get.return_value = Item(id="prod-1", config_id="cfg-1")

        result = eco_service.bind_product("eco-1", "prod-1", user_id=1)

        assert result.product_id == "prod-1"
        mock_session.add.assert_called_once_with(eco)

    def test_rejects_rebinding_to_different_product(self, eco_service, mock_session):
        """Cannot change product_id once bound."""
        eco = _make_eco(product_id="prod-1")
        eco_service.get_eco = MagicMock(return_value=eco)

        with pytest.raises(ValueError, match="already bound to product"):
            eco_service.bind_product("eco-1", "prod-2", user_id=1)

    def test_rejects_binding_when_target_version_exists(self, eco_service, mock_session):
        """Cannot bind product if target_version_id is already set."""
        eco = _make_eco(product_id=None, target_version_id="ver-99")
        eco_service.get_eco = MagicMock(return_value=eco)

        with pytest.raises(ValueError, match="already has a target_version_id"):
            eco_service.bind_product("eco-1", "prod-1", user_id=1)

    def test_rejects_binding_in_done_state(self, eco_service, mock_session):
        """Cannot bind product to a completed ECO."""
        eco = _make_eco(state=ECOState.DONE.value)
        eco_service.get_eco = MagicMock(return_value=eco)

        with pytest.raises(ValueError, match="must be draft or progress"):
            eco_service.bind_product("eco-1", "prod-1", user_id=1)

    def test_rejects_binding_in_canceled_state(self, eco_service, mock_session):
        eco = _make_eco(state=ECOState.CANCELED.value)
        eco_service.get_eco = MagicMock(return_value=eco)

        with pytest.raises(ValueError, match="must be draft or progress"):
            eco_service.bind_product("eco-1", "prod-1", user_id=1)

    def test_rejects_nonexistent_product(self, eco_service, mock_session):
        """Cannot bind to a product that doesn't exist."""
        eco = _make_eco(product_id=None)
        eco_service.get_eco = MagicMock(return_value=eco)
        mock_session.get.return_value = None  # product not found

        with pytest.raises(ValueError, match="not found"):
            eco_service.bind_product("eco-1", "prod-1", user_id=1)

    def test_can_create_target_revision(self, eco_service, mock_session):
        """With create_target_revision=True, also calls action_new_revision."""
        eco = _make_eco(product_id=None)
        eco_after_bind = _make_eco(product_id="prod-1", target_version_id="ver-new")
        eco_service.get_eco = MagicMock(side_effect=[eco, eco_after_bind])
        eco_service.action_new_revision = MagicMock()
        mock_session.get.return_value = Item(id="prod-1", config_id="cfg-1")

        result = eco_service.bind_product(
            "eco-1", "prod-1", user_id=1, create_target_revision=True
        )

        eco_service.action_new_revision.assert_called_once_with("eco-1", 1)

    def test_idempotent_bind_with_create_revision_when_no_target(
        self, eco_service, mock_session
    ):
        """Idempotent bind + create_target_revision creates revision if missing."""
        eco = _make_eco(product_id="prod-1", target_version_id=None)
        eco_after = _make_eco(product_id="prod-1", target_version_id="ver-new")
        eco_service.get_eco = MagicMock(side_effect=[eco, eco_after])
        eco_service.action_new_revision = MagicMock()

        result = eco_service.bind_product(
            "eco-1", "prod-1", user_id=1, create_target_revision=True
        )

        eco_service.action_new_revision.assert_called_once()

    def test_rejects_nonexistent_eco(self, eco_service, mock_session):
        eco_service.get_eco = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            eco_service.bind_product("eco-999", "prod-1", user_id=1)


class TestUpdateEcoFieldWhitelist:
    """Tests for the hardened update_eco with field whitelist."""

    def test_allows_whitelisted_fields(self, eco_service, mock_session):
        eco = _make_eco()
        eco_service.get_eco = MagicMock(return_value=eco)

        result = eco_service.update_eco(
            "eco-1", {"name": "New Name", "priority": "high"}, user_id=1
        )

        assert result.name == "New Name"
        assert result.priority == "high"

    def test_rejects_product_id_in_update(self, eco_service, mock_session):
        eco = _make_eco()
        eco_service.get_eco = MagicMock(return_value=eco)

        with pytest.raises(ValueError, match="cannot be updated via update_eco"):
            eco_service.update_eco("eco-1", {"product_id": "prod-1"}, user_id=1)

    def test_rejects_state_in_update(self, eco_service, mock_session):
        eco = _make_eco()
        eco_service.get_eco = MagicMock(return_value=eco)

        with pytest.raises(ValueError, match="cannot be updated via update_eco"):
            eco_service.update_eco("eco-1", {"state": "done"}, user_id=1)

    def test_rejects_update_in_done_state(self, eco_service, mock_session):
        eco = _make_eco(state=ECOState.DONE.value)
        eco_service.get_eco = MagicMock(return_value=eco)

        with pytest.raises(ValueError, match="must be draft or progress"):
            eco_service.update_eco("eco-1", {"name": "x"}, user_id=1)


class TestEcmCompatExecuteRejectsUnapproved:
    """Tests that legacy /ecm execute compat rejects unapproved ECOs."""

    def test_ecm_execute_compat_rejects_unapproved_eco(self, mock_session):
        from yuantus.meta_engine.services.legacy_ecm_compat_service import (
            LegacyEcmCompatService,
        )

        compat = LegacyEcmCompatService(mock_session)

        eco = _make_eco(state=ECOState.DRAFT.value)
        compat.eco_service = MagicMock()
        compat.eco_service.get_eco.return_value = eco

        with pytest.raises(ValueError, match="must be in 'approved' state"):
            compat.execute_eco_compat("eco-1", user_id=1)

    def test_ecm_execute_compat_rejects_progress_eco(self, mock_session):
        from yuantus.meta_engine.services.legacy_ecm_compat_service import (
            LegacyEcmCompatService,
        )

        compat = LegacyEcmCompatService(mock_session)

        eco = _make_eco(state=ECOState.PROGRESS.value)
        compat.eco_service = MagicMock()
        compat.eco_service.get_eco.return_value = eco

        with pytest.raises(ValueError, match="must be in 'approved' state"):
            compat.execute_eco_compat("eco-1", user_id=1)

    def test_ecm_affected_items_compat_rejects_non_change_action(self, mock_session):
        from yuantus.meta_engine.services.legacy_ecm_compat_service import (
            LegacyEcmCompatService,
        )

        compat = LegacyEcmCompatService(mock_session)
        compat.eco_service = MagicMock()

        with pytest.raises(ValueError, match="not supported via the legacy"):
            compat.add_affected_item_compat("eco-1", "item-1", "Release", user_id=1)

    def test_ecm_affected_items_compat_maps_to_bind_product(self, mock_session):
        from yuantus.meta_engine.services.legacy_ecm_compat_service import (
            LegacyEcmCompatService,
        )

        compat = LegacyEcmCompatService(mock_session)
        compat.eco_service = MagicMock()
        compat.eco_service.bind_product.return_value = _make_eco(product_id="prod-1")

        result = compat.add_affected_item_compat("eco-1", "prod-1", "Change", user_id=1)

        compat.eco_service.bind_product.assert_called_once_with(
            "eco-1", "prod-1", 1, create_target_revision=False
        )
