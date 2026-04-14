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
        mgr = CheckinManager(session, user_id=1)
        mgr.version_service = MagicMock(spec=VersionService)

        mgr.checkout("item1")

        mgr.version_service.checkout.assert_called_once_with(
            "item1", 1, comment="CAD Checkout"
        )

    def test_cad_checkin_delegates_to_version_service(self, session):
        """checkin() uploads native file, enqueues conversion jobs, then calls checkin."""
        mgr = CheckinManager(session, user_id=1)
        mgr.version_service = MagicMock(spec=VersionService)
        mgr.file_service = MagicMock()
        mock_native = MagicMock(id="file123")
        mgr.file_service.upload_file.return_value = mock_native

        mock_item = MagicMock()
        mock_item.current_version_id = "ver-abc"
        session.get.return_value = mock_item

        preview_job = MagicMock()
        preview_job.id = "job-preview"
        geometry_job = MagicMock()
        geometry_job.id = "job-geometry"

        with patch(
            "yuantus.meta_engine.services.job_service.JobService"
        ) as MockJobService:
            MockJobService.return_value.create_job.side_effect = [
                preview_job,
                geometry_job,
            ]
            mgr.checkin("item1", b"content", "test.cad")

        mgr.version_service.checkin.assert_called_once()
        args, kwargs = mgr.version_service.checkin.call_args
        assert args[0] == "item1"
        assert kwargs["properties"]["native_file"] == "file123"
        assert kwargs["properties"]["cad_conversion_job_ids"] == [
            "job-preview",
            "job-geometry",
        ]
        assert "viewable_file" not in kwargs["properties"]

    def test_cad_checkin_enqueues_preview_and_geometry_jobs(self, session):
        mgr = CheckinManager(session, user_id=7)
        mgr.version_service = MagicMock(spec=VersionService)
        mgr.file_service = MagicMock()
        mgr.file_service.upload_file.return_value = MagicMock(id="file-native")

        mock_item = MagicMock()
        mock_item.current_version_id = "ver-xyz"
        session.get.return_value = mock_item

        mock_job = MagicMock()
        mock_job.id = "job-x"

        with patch(
            "yuantus.meta_engine.services.job_service.JobService"
        ) as MockJobService:
            MockJobService.return_value.create_job.return_value = mock_job
            mgr.checkin("item1", b"data", "part.stp")
            create_calls = MockJobService.return_value.create_job.call_args_list

        task_types = [c[0][0] for c in create_calls]
        assert "cad_preview" in task_types
        assert "cad_geometry" in task_types

        geom_call = next(c for c in create_calls if c[0][0] == "cad_geometry")
        assert geom_call[0][1].get("target_format") == "glTF"

        for c in create_calls:
            assert c[0][1].get("version_id") == "ver-xyz"

    def test_cad_checkin_does_not_call_subprocess(self, session):
        mgr = CheckinManager(session, user_id=1)
        mgr.version_service = MagicMock(spec=VersionService)
        mgr.file_service = MagicMock()
        mgr.file_service.upload_file.return_value = MagicMock(id="f1")
        session.get.return_value = MagicMock(current_version_id="v1")

        with patch(
            "yuantus.meta_engine.services.job_service.JobService"
        ) as MockJobService:
            MockJobService.return_value.create_job.return_value = MagicMock(id="j1")
            with patch("subprocess.run") as mock_sub:
                mgr.checkin("item1", b"x", "a.stp")
                mock_sub.assert_not_called()
