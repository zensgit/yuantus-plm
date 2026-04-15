"""
Focused regression for the minimal CAD checkin queue slice.
"""

import pytest
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.services.checkin_service import CheckinManager
from yuantus.meta_engine.services.job_worker import JobWorker
from yuantus.meta_engine.version.service import VersionService


def _make_manager(session, user_id=1):
    mgr = CheckinManager(session, user_id=user_id)
    mgr.version_service = MagicMock(spec=VersionService)
    mgr.file_service = MagicMock()
    return mgr


def _setup_session_item(session, version_id="ver-1"):
    mock_item = MagicMock()
    mock_item.current_version_id = version_id
    session.get.return_value = mock_item
    return mock_item


class TestCheckinTransactionChain:
    @pytest.fixture
    def session(self):
        return MagicMock()

    def test_native_file_id_and_job_ids_written_to_version_properties(self, session):
        mgr = _make_manager(session)
        mgr.file_service.upload_file.return_value = MagicMock(id="nat-42")
        _setup_session_item(session)

        with patch(
            "yuantus.meta_engine.services.job_service.JobService"
        ) as MockJS:
            MockJS.return_value.create_job.side_effect = [
                MagicMock(id="job-preview"),
                MagicMock(id="job-geometry"),
            ]
            mgr.checkin("item-1", b"x", "x.stp")

        _, kwargs = mgr.version_service.checkin.call_args
        assert kwargs["properties"]["native_file"] == "nat-42"
        assert kwargs["properties"]["cad_conversion_job_ids"] == [
            "job-preview",
            "job-geometry",
        ]

    def test_jobs_carry_version_id_for_binding(self, session):
        mgr = _make_manager(session)
        mgr.file_service.upload_file.return_value = MagicMock(id="fn")
        _setup_session_item(session, version_id="ver-binding")

        with patch(
            "yuantus.meta_engine.services.job_service.JobService"
        ) as MockJS:
            MockJS.return_value.create_job.return_value = MagicMock(id="j")
            mgr.checkin("item-1", b"z", "z.stp")
            calls = MockJS.return_value.create_job.call_args_list

        for c in calls:
            assert c[0][1].get("version_id") == "ver-binding"
            assert c[0][1].get("file_id") == "fn"
            assert c[0][1].get("item_id") == "item-1"


class TestWorkerDerivedFileBinding:
    def test_worker_binds_derived_files_on_completion(self):
        mock_job = MagicMock()
        mock_job.id = "job-99"
        mock_job.task_type = "cad_preview"
        mock_job.payload = {"file_id": "f-native", "version_id": "ver-9"}
        mock_job.created_by_id = 1

        mock_job_service = MagicMock()
        mock_job_service.session = MagicMock()

        worker = JobWorker(worker_id="test-worker")
        worker.register_handler(
            "cad_preview",
            lambda payload: {
                "derived_files": [
                    {
                        "file_id": "derived-preview-1",
                        "file_role": "preview",
                        "version_id": "ver-9",
                    }
                ]
            },
        )

        with patch(
            "yuantus.meta_engine.version.file_service.VersionFileService"
        ) as MockVFS:
            MockVFS.return_value.get_blocking_file_locks.return_value = []
            worker._execute_job(mock_job, mock_job_service)

        MockVFS.return_value.attach_file.assert_called_once_with(
            version_id="ver-9",
            file_id="derived-preview-1",
            file_role="preview",
            user_id=1,
        )
        mock_job_service.session.commit.assert_called()

    def test_worker_syncs_current_version_files_back_to_item(self):
        mock_job = MagicMock()
        mock_job.id = "job-sync"
        mock_job.task_type = "cad_geometry"
        mock_job.payload = {"file_id": "fn", "version_id": "ver-sync"}
        mock_job.created_by_id = 1

        mock_job_service = MagicMock()
        mock_job_service.session = MagicMock()
        mock_version = MagicMock()
        mock_version.is_current = True
        mock_version.item_id = "item-sync"
        mock_job_service.session.get.return_value = mock_version

        worker = JobWorker(worker_id="test-worker")
        worker.register_handler(
            "cad_geometry",
            lambda payload: {
                "derived_files": [
                    {"file_id": "fn", "file_role": "geometry", "version_id": "ver-sync"}
                ]
            },
        )

        with patch(
            "yuantus.meta_engine.version.file_service.VersionFileService"
        ) as MockVFS:
            MockVFS.return_value.get_blocking_file_locks.return_value = []
            worker._execute_job(mock_job, mock_job_service)

        MockVFS.return_value.sync_version_files_to_item.assert_called_once_with(
            version_id="ver-sync",
            item_id="item-sync",
            user_id=1,
            remove_missing=False,
        )

    def test_worker_passes_null_user_id_when_job_has_no_creator(self):
        mock_job = MagicMock()
        mock_job.id = "job-anon"
        mock_job.task_type = "cad_preview"
        mock_job.payload = {"file_id": "f-native", "version_id": "ver-9"}
        mock_job.created_by_id = None

        mock_job_service = MagicMock()
        mock_job_service.session = MagicMock()

        worker = JobWorker(worker_id="test-worker")
        worker.register_handler(
            "cad_preview",
            lambda payload: {
                "derived_files": [
                    {
                        "file_id": "derived-preview-1",
                        "file_role": "preview",
                        "version_id": "ver-9",
                    }
                ]
            },
        )

        with patch(
            "yuantus.meta_engine.version.file_service.VersionFileService"
        ) as MockVFS:
            MockVFS.return_value.get_blocking_file_locks.return_value = []
            worker._execute_job(mock_job, mock_job_service)

        MockVFS.return_value.attach_file.assert_called_once_with(
            version_id="ver-9",
            file_id="derived-preview-1",
            file_role="preview",
            user_id=None,
        )

    def test_worker_skips_binding_when_version_has_foreign_file_locks(self):
        mock_job = MagicMock()
        mock_job.id = "job-locked"
        mock_job.task_type = "cad_preview"
        mock_job.payload = {"file_id": "f-native", "version_id": "ver-locked"}
        mock_job.created_by_id = 7

        mock_job_service = MagicMock()
        mock_job_service.session = MagicMock()

        worker = JobWorker(worker_id="test-worker")
        worker.register_handler(
            "cad_preview",
            lambda payload: {
                "derived_files": [
                    {
                        "file_id": "derived-preview-1",
                        "file_role": "preview",
                        "version_id": "ver-locked",
                    }
                ]
            },
        )

        with patch(
            "yuantus.meta_engine.version.file_service.VersionFileService"
        ) as MockVFS:
            MockVFS.return_value.get_blocking_file_locks.return_value = [
                MagicMock(checked_out_by_id=9)
            ]
            worker._execute_job(mock_job, mock_job_service)

        MockVFS.return_value.attach_file.assert_not_called()
        MockVFS.return_value.sync_version_files_to_item.assert_not_called()
