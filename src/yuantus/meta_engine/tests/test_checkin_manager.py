from sqlalchemy.orm import Session
from yuantus.meta_engine.services.checkin_service import CheckinManager
from yuantus.meta_engine.version.service import VersionService
import pytest
from unittest.mock import MagicMock, patch, call


class TestCheckinRefactor:
    @pytest.fixture
    def session(self):
        return MagicMock(spec=Session)

    def test_cad_checkout_delegates_to_version_service(self, session):
        mgr = CheckinManager(session, user_id=1)
        mgr.version_service = MagicMock(spec=VersionService)
        mgr.checkout("item1")
        mgr.version_service.checkout.assert_called_once_with(
            "item1", 1, comment="CAD Checkout"
        )

    def test_cad_checkin_delegates_to_version_service(self, session):
        mgr = CheckinManager(session, user_id=1)
        mgr.version_service = MagicMock(spec=VersionService)
        mgr.file_service = MagicMock()
        mgr.file_service.upload_file.return_value = MagicMock(id="file123")
        session.get.return_value = MagicMock(current_version_id="ver-abc")

        with patch("yuantus.meta_engine.services.job_service.JobService") as MockJS:
            MockJS.return_value.create_job.return_value = MagicMock(id="j1")
            mgr.checkin("item1", b"content", "test.cad")

        mgr.version_service.checkin.assert_called_once()
        _, kwargs = mgr.version_service.checkin.call_args
        assert kwargs["properties"]["native_file"] == "file123"
        assert "viewable_file" not in kwargs["properties"]

    def test_cad_checkin_enqueues_preview_and_geometry_jobs(self, session):
        mgr = CheckinManager(session, user_id=7)
        mgr.version_service = MagicMock(spec=VersionService)
        mgr.file_service = MagicMock()
        mgr.file_service.upload_file.return_value = MagicMock(id="f-native")
        session.get.return_value = MagicMock(current_version_id="ver-xyz")

        with patch("yuantus.meta_engine.services.job_service.JobService") as MockJS:
            MockJS.return_value.create_job.return_value = MagicMock(id="jx")
            mgr.checkin("item1", b"data", "part.stp")
            calls = MockJS.return_value.create_job.call_args_list

        types = [c[0][0] for c in calls]
        assert "cad_preview" in types
        assert "cad_geometry" in types
        geom = next(c for c in calls if c[0][0] == "cad_geometry")
        assert geom[0][1].get("target_format") == "glTF"

    def test_cad_checkin_does_not_call_subprocess(self, session):
        mgr = CheckinManager(session, user_id=1)
        mgr.version_service = MagicMock(spec=VersionService)
        mgr.file_service = MagicMock()
        mgr.file_service.upload_file.return_value = MagicMock(id="f1")
        session.get.return_value = MagicMock(current_version_id="v1")

        with patch("yuantus.meta_engine.services.job_service.JobService") as MockJS:
            MockJS.return_value.create_job.return_value = MagicMock(id="j1")
            with patch("subprocess.run") as mock_sub:
                mgr.checkin("item1", b"x", "a.stp")
                mock_sub.assert_not_called()
