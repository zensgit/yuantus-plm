from sqlalchemy.orm import Session
from yuantus.meta_engine.services.checkin_service import CheckinManager
from yuantus.meta_engine.version.service import VersionService
import pytest
from unittest.mock import MagicMock, patch


class TestCheckinRefactor:
    @pytest.fixture
    def session(self):
        return MagicMock(spec=Session)

    def test_cad_checkout_delegates_to_version_service(self, session):
        # Arrange
        mgr = CheckinManager(session, user_id=1)
        # Mock internal version service
        mgr.version_service = MagicMock(spec=VersionService)

        # Act
        mgr.checkout("item1")

        # Assert
        mgr.version_service.checkout.assert_called_once_with(
            "item1", 1, comment="CAD Checkout"
        )

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_cad_checkin_delegates_to_version_service(
        self, mock_exists, mock_run, session
    ):
        # Arrange
        mgr = CheckinManager(session, user_id=1)
        mgr.version_service = MagicMock(spec=VersionService)
        mgr.file_service = MagicMock()
        mgr.file_service.upload_file.return_value = MagicMock(id="file123")
        mgr.file_service.get_file_path.return_value = "/tmp/test.cad"

        mock_exists.return_value = True  # File exists

        # Act
        mgr.checkin("item1", b"content", "test.cad")

        # Assert
        # Check args passed to version_service.checkin
        mgr.version_service.checkin.assert_called_once()
        args, kwargs = mgr.version_service.checkin.call_args
        assert args[0] == "item1"
        assert kwargs["properties"]["native_file"] == "file123"
        # Viewable should be set if path exists (mocked true)
        assert "viewable_file" in kwargs["properties"]
