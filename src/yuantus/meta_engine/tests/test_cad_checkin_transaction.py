"""
P1-4 + P1-5 + P1-4.2: CAD Checkin Transaction Chain + Worker Binding + ItemFile Sync
"""
import pytest
from unittest.mock import MagicMock, patch
from yuantus.meta_engine.services.checkin_service import CheckinManager
from yuantus.meta_engine.services.job_worker import JobWorker
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.version.service import VersionService


def _mgr(session, uid=1):
    m = CheckinManager(session, user_id=uid)
    m.version_service = MagicMock(spec=VersionService)
    m.file_service = MagicMock()
    return m


class TestCheckinJobQueue:
    @pytest.fixture
    def session(self):
        return MagicMock()

    def test_native_uploaded(self, session):
        mgr = _mgr(session); mgr.file_service.upload_file.return_value = MagicMock(id="n1")
        session.get.return_value = MagicMock(current_version_id="v1")
        with patch("yuantus.meta_engine.services.job_service.JobService") as JS:
            JS.return_value.create_job.return_value = MagicMock(id="j")
            mgr.checkin("i1", b"x", "p.stp")
        mgr.file_service.upload_file.assert_called_once_with(b"x", "p.stp")

    def test_jobs_carry_version_id(self, session):
        mgr = _mgr(session); mgr.file_service.upload_file.return_value = MagicMock(id="fn")
        session.get.return_value = MagicMock(current_version_id="ver-bind")
        with patch("yuantus.meta_engine.services.job_service.JobService") as JS:
            JS.return_value.create_job.return_value = MagicMock(id="j")
            mgr.checkin("i1", b"z", "z.stp")
            for c in JS.return_value.create_job.call_args_list:
                assert c[0][1].get("version_id") == "ver-bind"

    def test_max_attempts_3(self, session):
        mgr = _mgr(session); mgr.file_service.upload_file.return_value = MagicMock(id="fn")
        session.get.return_value = MagicMock(current_version_id="v1")
        with patch("yuantus.meta_engine.services.job_service.JobService") as JS:
            JS.return_value.create_job.return_value = MagicMock(id="j")
            mgr.checkin("i1", b"r", "r.stp")
            for c in JS.return_value.create_job.call_args_list:
                assert c[1].get("max_attempts") == 3

    def test_cad_format_from_ext(self, session):
        mgr = _mgr(session); mgr.file_service.upload_file.return_value = MagicMock(id="fn")
        session.get.return_value = MagicMock(current_version_id="v1")
        with patch("yuantus.meta_engine.services.job_service.JobService") as JS:
            JS.return_value.create_job.return_value = MagicMock(id="j")
            mgr.checkin("i1", b"x", "model.STEP")
            for c in JS.return_value.create_job.call_args_list:
                assert c[0][1].get("cad_format") == "STEP"


class TestWorkerDerivedFileBinding:
    def test_binds_derived_files(self):
        job = MagicMock(id="j1", task_type="cad_preview",
                        payload={"file_id":"fn","version_id":"v9"}, created_by_id=1)
        w = JobWorker(worker_id="w")
        w.register_handler("cad_preview", lambda p: {
            "derived_files":[{"file_id":"d1","file_role":"preview","version_id":"v9"}]
        })
        js = MagicMock(); js.session = MagicMock()
        with patch("yuantus.meta_engine.version.file_service.VersionFileService") as VFS:
            w._execute_job(job, js)
        VFS.return_value.attach_file.assert_called_once_with(
            version_id="v9", file_id="d1", file_role="preview")

    def test_fallback_version_id_from_payload(self):
        job = MagicMock(id="j2", task_type="cad_geometry",
                        payload={"file_id":"fn","version_id":"vfb"}, created_by_id=1)
        w = JobWorker(worker_id="w")
        w.register_handler("cad_geometry", lambda p: {
            "derived_files":[{"file_id":"dg","file_role":"geometry"}]
        })
        js = MagicMock(); js.session = MagicMock()
        with patch("yuantus.meta_engine.version.file_service.VersionFileService") as VFS:
            w._execute_job(job, js)
        VFS.return_value.attach_file.assert_called_once_with(
            version_id="vfb", file_id="dg", file_role="geometry")

    def test_bind_failure_does_not_fail_job(self):
        job = MagicMock(id="j3", task_type="cad_preview",
                        payload={"file_id":"fn","version_id":"ve"}, created_by_id=1)
        w = JobWorker(worker_id="w")
        w.register_handler("cad_preview", lambda p: {
            "derived_files":[{"file_id":"d1","file_role":"preview","version_id":"ve"}]
        })
        js = MagicMock(); js.session = MagicMock()
        with patch("yuantus.meta_engine.version.file_service.VersionFileService") as VFS:
            VFS.return_value.attach_file.side_effect = Exception("DB")
            w._execute_job(job, js)
        js.complete_job.assert_called_once()
        js.fail_job.assert_not_called()

    def test_skip_when_no_version_id(self):
        job = MagicMock(id="j4", task_type="cad_preview",
                        payload={"file_id":"fn"}, created_by_id=1)
        w = JobWorker(worker_id="w")
        w.register_handler("cad_preview", lambda p: {
            "derived_files":[{"file_id":"d1","file_role":"preview"}]
        })
        js = MagicMock(); js.session = MagicMock()
        with patch("yuantus.meta_engine.version.file_service.VersionFileService") as VFS:
            w._execute_job(job, js)
        VFS.return_value.attach_file.assert_not_called()
        js.complete_job.assert_called_once()

    def test_sync_item_for_current_version(self):
        job = MagicMock(id="j5", task_type="cad_preview",
                        payload={"file_id":"fn","version_id":"vc"}, created_by_id=1)
        ver = MagicMock(is_current=True, item_id="item-42")
        w = JobWorker(worker_id="w")
        w.register_handler("cad_preview", lambda p: {
            "derived_files":[{"file_id":"fc","file_role":"preview","version_id":"vc"}]
        })
        js = MagicMock(); js.session = MagicMock(); js.session.get.return_value = ver
        with patch("yuantus.meta_engine.version.file_service.VersionFileService") as VFS:
            w._execute_job(job, js)
        VFS.return_value.sync_version_files_to_item.assert_called_once_with(
            version_id="vc", item_id="item-42", remove_missing=False)

    def test_no_sync_for_non_current(self):
        job = MagicMock(id="j6", task_type="cad_preview",
                        payload={"file_id":"fn","version_id":"vo"}, created_by_id=1)
        ver = MagicMock(is_current=False)
        w = JobWorker(worker_id="w")
        w.register_handler("cad_preview", lambda p: {
            "derived_files":[{"file_id":"fc","file_role":"preview","version_id":"vo"}]
        })
        js = MagicMock(); js.session = MagicMock(); js.session.get.return_value = ver
        with patch("yuantus.meta_engine.version.file_service.VersionFileService") as VFS:
            w._execute_job(job, js)
        VFS.return_value.attach_file.assert_called_once()
        VFS.return_value.sync_version_files_to_item.assert_not_called()


class TestEnrichDerivedFiles:
    def test_enriches_ok_result(self):
        from yuantus.meta_engine.tasks.cad_pipeline_tasks import _enrich_with_derived_files
        r = _enrich_with_derived_files({"ok":True,"file_id":"f1"},{"version_id":"v1"},"preview")
        assert r["derived_files"] == [{"file_id":"f1","file_role":"preview","version_id":"v1"}]

    def test_skips_failed(self):
        from yuantus.meta_engine.tasks.cad_pipeline_tasks import _enrich_with_derived_files
        r = _enrich_with_derived_files({"ok":False,"file_id":"f1"},{"version_id":"v1"},"preview")
        assert "derived_files" not in r

    def test_skips_no_version_id(self):
        from yuantus.meta_engine.tasks.cad_pipeline_tasks import _enrich_with_derived_files
        r = _enrich_with_derived_files({"ok":True,"file_id":"f1"},{},"preview")
        assert "derived_files" not in r

    def test_preview_wrapper(self):
        with patch("yuantus.meta_engine.tasks.cad_pipeline_tasks.cad_preview") as m:
            m.return_value = {"ok":True,"file_id":"fc1"}
            from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_preview_with_binding
            r = cad_preview_with_binding({"file_id":"fc1","version_id":"va"}, MagicMock())
        assert r["derived_files"][0]["file_role"] == "preview"

    def test_geometry_wrapper(self):
        with patch("yuantus.meta_engine.tasks.cad_pipeline_tasks.cad_geometry") as m:
            m.return_value = {"ok":True,"file_id":"fc2","target_format":"gltf"}
            from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_geometry_with_binding
            r = cad_geometry_with_binding({"file_id":"fc2","version_id":"vb"}, MagicMock())
        assert r["derived_files"][0]["file_role"] == "geometry"


class TestVersionFileDedupAndLockRelease:
    def test_stale_preview_replaced(self):
        from yuantus.meta_engine.version.file_service import VersionFileService
        session = MagicMock()
        ver = MagicMock(file_count=2)
        session.get.side_effect = lambda cls, id_: {
            "ItemVersion": ver, "FileContainer": MagicMock(system_path="/p")
        }.get(cls.__name__)
        session.query.return_value.filter_by.return_value.first.return_value = None
        stale = MagicMock(file_id="old-fc")
        session.query.return_value.filter_by.return_value.filter.return_value.all.return_value = [stale]
        svc = VersionFileService(session)
        svc.attach_file("v1", "new-fc", file_role="preview")
        session.delete.assert_called_once_with(stale)

    def test_release_all_file_locks(self):
        from yuantus.meta_engine.version.file_service import VersionFileService
        session = MagicMock()
        vf1 = MagicMock(checked_out_by_id=7)
        vf2 = MagicMock(checked_out_by_id=8)
        session.query.return_value.filter.return_value.all.return_value = [vf1, vf2]
        svc = VersionFileService(session)
        n = svc.release_all_file_locks("v1")
        assert n == 2
        assert vf1.checked_out_by_id is None
        assert vf2.checked_out_by_id is None

    def test_checkin_calls_release_all(self):
        from yuantus.meta_engine.version.service import VersionService
        session = MagicMock()
        item = MagicMock(current_version_id="vA", properties={})
        ver = MagicMock(id="vA", item_id="i1", checked_out_by_id=7, properties={})
        with patch.object(session, 'query') as mq:
            mq.return_value.filter_by.return_value.one.side_effect = [item, ver]
            svc = VersionService(session)
            svc.file_version_service = MagicMock()
            svc.checkin("i1", 7, comment="done")
        svc.file_version_service.release_all_file_locks.assert_called_once_with("vA")
