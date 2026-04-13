"""
Tests for the Legacy ECM Compatibility Router
==============================================
PR-3 of PLM core convergence.

Replaces test_change_service.py. Tests that the /ecm compat shim correctly
delegates to canonical ECOService and handles edge cases.

These tests validate the compat BEHAVIOR, not the old ChangeService logic.
"""

import pytest
from unittest.mock import MagicMock

from yuantus.meta_engine.services.legacy_ecm_compat_service import (
    LegacyEcmCompatService,
)
from yuantus.meta_engine.models.eco import ECO, ECOState


def _make_eco(eco_id="eco-1", state="draft", product_id=None):
    return ECO(
        id=eco_id,
        name="Test",
        eco_type="bom",
        state=state,
        product_id=product_id,
        created_by_id=1,
    )


class TestEcmCompatImpactAnalysis:
    def test_returns_old_shape(self):
        """Impact analysis returns {where_used, pending_changes} shape."""
        from unittest.mock import patch as mock_patch

        session = MagicMock()
        compat = LegacyEcmCompatService(session)

        # Mock the query for open ECOs
        session.query.return_value.filter.return_value.all.return_value = [
            _make_eco(state=ECOState.PROGRESS.value, product_id="item-1")
        ]

        with mock_patch(
            "yuantus.meta_engine.services.legacy_ecm_compat_service.ImpactAnalysisService"
        ) as mock_impact:
            mock_impact.return_value.where_used.return_value = [
                {"parent_id": "assy-1"}
            ]

            result = compat.get_impact_analysis("item-1")

        assert "where_used" in result
        assert "pending_changes" in result
        assert len(result["pending_changes"]) == 1


class TestEcmCompatAffectedItems:
    def test_maps_change_to_bind_product(self):
        """POST affected-items with action=Change calls bind_product."""
        session = MagicMock()
        compat = LegacyEcmCompatService(session)
        compat.eco_service = MagicMock()
        compat.eco_service.bind_product.return_value = _make_eco(product_id="prod-1")

        result = compat.add_affected_item_compat("eco-1", "prod-1", "Change", 1)

        compat.eco_service.bind_product.assert_called_once_with(
            "eco-1", "prod-1", 1, create_target_revision=False
        )
        assert result["product_id"] == "prod-1"

    def test_rejects_release_action(self):
        session = MagicMock()
        compat = LegacyEcmCompatService(session)

        with pytest.raises(ValueError, match="not supported via the legacy"):
            compat.add_affected_item_compat("eco-1", "item-1", "Release", 1)

    def test_rejects_revise_action(self):
        session = MagicMock()
        compat = LegacyEcmCompatService(session)

        with pytest.raises(ValueError, match="not supported via the legacy"):
            compat.add_affected_item_compat("eco-1", "item-1", "Revise", 1)

    def test_rejects_new_generation_action(self):
        session = MagicMock()
        compat = LegacyEcmCompatService(session)

        with pytest.raises(ValueError, match="not supported via the legacy"):
            compat.add_affected_item_compat("eco-1", "item-1", "New Generation", 1)


class TestEcmCompatExecute:
    def test_rejects_draft_eco(self):
        session = MagicMock()
        compat = LegacyEcmCompatService(session)
        compat.eco_service = MagicMock()
        compat.eco_service.get_eco.return_value = _make_eco(state=ECOState.DRAFT.value)

        with pytest.raises(ValueError, match="must be in 'approved' state"):
            compat.execute_eco_compat("eco-1", 1)

    def test_rejects_progress_eco(self):
        session = MagicMock()
        compat = LegacyEcmCompatService(session)
        compat.eco_service = MagicMock()
        compat.eco_service.get_eco.return_value = _make_eco(
            state=ECOState.PROGRESS.value
        )

        with pytest.raises(ValueError, match="must be in 'approved' state"):
            compat.execute_eco_compat("eco-1", 1)

    def test_rejects_suspended_eco(self):
        session = MagicMock()
        compat = LegacyEcmCompatService(session)
        compat.eco_service = MagicMock()
        compat.eco_service.get_eco.return_value = _make_eco(
            state=ECOState.SUSPENDED.value
        )

        with pytest.raises(ValueError, match="must be in 'approved' state"):
            compat.execute_eco_compat("eco-1", 1)

    def test_rejects_nonexistent_eco(self):
        session = MagicMock()
        compat = LegacyEcmCompatService(session)
        compat.eco_service = MagicMock()
        compat.eco_service.get_eco.return_value = None

        with pytest.raises(ValueError, match="not found"):
            compat.execute_eco_compat("eco-999", 1)

    def test_approved_eco_runs_diagnostics_then_apply(self):
        """Approved ECO runs diagnostics check before apply."""
        session = MagicMock()
        compat = LegacyEcmCompatService(session)
        compat.eco_service = MagicMock()
        compat.eco_service.get_eco.return_value = _make_eco(
            state=ECOState.APPROVED.value
        )
        compat.eco_service.get_apply_diagnostics.return_value = {
            "errors": [],
            "warnings": [],
        }

        result = compat.execute_eco_compat("eco-1", 1)

        compat.eco_service.get_apply_diagnostics.assert_called_once_with("eco-1", 1)
        compat.eco_service.action_apply.assert_called_once_with("eco-1", 1)
        assert result["status"] == "success"

    def test_approved_eco_blocked_by_diagnostics(self):
        """Approved ECO blocked when diagnostics report errors."""
        session = MagicMock()
        compat = LegacyEcmCompatService(session)
        compat.eco_service = MagicMock()
        compat.eco_service.get_eco.return_value = _make_eco(
            state=ECOState.APPROVED.value
        )
        compat.eco_service.get_apply_diagnostics.return_value = {
            "errors": [{"message": "Routing not released"}],
            "warnings": [],
        }

        with pytest.raises(ValueError, match="Routing not released"):
            compat.execute_eco_compat("eco-1", 1)

        compat.eco_service.action_apply.assert_not_called()
