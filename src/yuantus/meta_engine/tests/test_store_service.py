import pytest
from unittest.mock import MagicMock
from yuantus.meta_engine.app_framework.store_service import AppStoreService
from yuantus.meta_engine.app_framework.store_models import (
    MarketplaceAppListing,
)


class TestAppStoreService:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    def test_sync_store(self, mock_session):
        service = AppStoreService(mock_session)

        # Mock query return
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        service.sync_store_listings()

        # Should add 2 mock apps
        assert mock_session.add.call_count >= 2

    def test_purchase_app(self, mock_session):
        service = AppStoreService(mock_session)

        # Mock listing
        listing = MarketplaceAppListing(id="l1", name="app", price_model="Paid")
        mock_session.query.return_value.get.return_value = listing

        lic = service.purchase_app("l1")
        assert lic.status == "Active"
        mock_session.add.assert_called()

    def test_install_paid_without_license_fails(self, mock_session):
        service = AppStoreService(mock_session)

        listing = MarketplaceAppListing(id="l1", name="app", price_model="Paid")
        mock_session.query.return_value.get.return_value = listing

        # Mock no license found
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        with pytest.raises(ValueError, match="No active license"):
            service.install_from_store("l1", 1)
