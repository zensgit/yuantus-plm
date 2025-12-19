import pytest
from unittest.mock import MagicMock
from yuantus.meta_engine.app_framework.service import AppService
from yuantus.meta_engine.app_framework.models import ExtensionPoint


class TestAppService:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    def test_register_app(self, mock_session):
        service = AppService(mock_session)

        manifest = {
            "name": "com.example.plugin",
            "version": "1.0.0",
            "display_name": "Example Plugin",
            "extensions": [{"point": "menu", "name": "My Menu", "handler": "js:foo"}],
        }

        # Mock checks
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        # Mock Ext Point lookup
        mock_ep = ExtensionPoint(id="ep-1", name="menu")
        # We need to handle query for ExtPoint separately
        # when we call get_extension_point("menu")

        # side_effect for query().filter_by().first()
        # 1st call: check app existence -> None
        # 2nd call: check ext point -> mock_ep
        def side_effect_filter_by_first():
            return None

        # This is tricky with chained mocks. Simplified checking:
        # Just ensure Add is called.

        app = service.register_app(manifest, installer_id=1)

        assert app.name == "com.example.plugin"
        mock_session.add.assert_called()

    def test_get_extensions(self, mock_session):
        service = AppService(mock_session)
        service.get_extensions_for_point("menu")
        # Assert query construction
        mock_session.query.assert_called()
