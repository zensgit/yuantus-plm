"""
P1-4.1 + Fix 2/3: file_router → meta_conversion_jobs convergence tests.
"""
import pytest
from unittest.mock import MagicMock, patch
from yuantus.meta_engine.web.file_router import (
    _meta_job_to_response, ConversionJobResponse, _PREVIEW_FORMATS,
)


class TestMetaJobToResponse:
    def test_maps_preview(self):
        j = MagicMock(id="j1", task_type="cad_preview",
                      payload={"file_id": "fc-1"}, status="pending", last_error=None)
        r = _meta_job_to_response(j)
        assert r.source_file_id == "fc-1"
        assert r.target_format == "png"
        assert r.operation_type == "preview"

    def test_maps_geometry(self):
        j = MagicMock(id="j2", task_type="cad_geometry",
                      payload={"file_id": "fc-2", "target_format": "gltf"},
                      status="completed", last_error=None)
        r = _meta_job_to_response(j)
        assert r.target_format == "gltf"
        assert r.operation_type == "convert"

    def test_result_file_id_from_completed_payload(self):
        """Fix 2: completed jobs surface result_file_id from payload.result"""
        j = MagicMock(id="j3", task_type="cad_geometry",
                      payload={"file_id": "fc-3", "result": {"file_id": "fc-3"}},
                      status="completed", last_error=None)
        r = _meta_job_to_response(j)
        assert r.result_file_id == "fc-3"

    def test_result_file_id_none_for_pending(self):
        """Fix 2: non-completed → result_file_id is None"""
        j = MagicMock(id="j4", task_type="cad_geometry",
                      payload={"file_id": "fc-4"}, status="pending", last_error=None)
        r = _meta_job_to_response(j)
        assert r.result_file_id is None


class TestPreviewFormats:
    def test_png_is_preview(self):
        assert "png" in _PREVIEW_FORMATS

    def test_gltf_is_not_preview(self):
        assert "gltf" not in _PREVIEW_FORMATS


class TestConvertEndpoint:
    def test_geometry_format_creates_cad_geometry_job(self):
        from yuantus.meta_engine.web.file_router import request_conversion
        import asyncio
        db = MagicMock()
        fc = MagicMock(); fc.is_cad_file.return_value = True
        fc.filename = "p.stp"; fc.get_extension.return_value = "stp"
        db.get.return_value = fc
        job = MagicMock(id="j", task_type="cad_geometry",
                        payload={"file_id":"fc","target_format":"gltf"},
                        status="pending", last_error=None)
        with patch("yuantus.meta_engine.web.file_router.JobService") as JS:
            JS.return_value.create_job.return_value = job
            r = asyncio.get_event_loop().run_until_complete(
                request_conversion("fc", "gltf", db)
            )
        assert JS.return_value.create_job.call_args[0][0] == "cad_geometry"
        assert r.operation_type == "convert"

    def test_png_format_creates_cad_preview_job(self):
        from yuantus.meta_engine.web.file_router import request_conversion
        import asyncio
        db = MagicMock()
        fc = MagicMock(); fc.is_cad_file.return_value = True
        fc.filename = "p.stp"; fc.get_extension.return_value = "stp"
        db.get.return_value = fc
        job = MagicMock(id="jp", task_type="cad_preview",
                        payload={"file_id":"fc"}, status="pending", last_error=None)
        with patch("yuantus.meta_engine.web.file_router.JobService") as JS:
            JS.return_value.create_job.return_value = job
            asyncio.get_event_loop().run_until_complete(
                request_conversion("fc", "png", db)
            )
        assert JS.return_value.create_job.call_args[0][0] == "cad_preview"

    def test_does_not_call_cad_converter_service(self):
        from yuantus.meta_engine.web.file_router import request_conversion
        import asyncio
        db = MagicMock()
        fc = MagicMock(); fc.is_cad_file.return_value = True
        fc.filename = "p.stp"; fc.get_extension.return_value = "stp"
        db.get.return_value = fc
        job = MagicMock(id="j", task_type="cad_geometry",
                        payload={"file_id":"fc"}, status="pending", last_error=None)
        with patch("yuantus.meta_engine.web.file_router.JobService") as JS, \
             patch("yuantus.meta_engine.web.file_router.CADConverterService") as CAD:
            JS.return_value.create_job.return_value = job
            asyncio.get_event_loop().run_until_complete(
                request_conversion("fc", "obj", db)
            )
        CAD.return_value.create_conversion_job.assert_not_called()


class TestConversionStatusDualRead:
    def test_meta_jobs_table_first(self):
        from yuantus.meta_engine.web.file_router import get_conversion_status
        import asyncio
        db = MagicMock()
        meta = MagicMock(id="m1", task_type="cad_preview",
                         payload={"file_id":"fc"}, status="completed", last_error=None)
        from yuantus.meta_engine.web.file_router import MetaConversionJob
        db.get = MagicMock(side_effect=lambda cls, jid: meta if cls is MetaConversionJob else None)
        r = asyncio.get_event_loop().run_until_complete(get_conversion_status("m1", db))
        assert r.id == "m1"

    def test_fallback_to_legacy(self):
        from yuantus.meta_engine.web.file_router import get_conversion_status
        import asyncio
        db = MagicMock()
        legacy = MagicMock(id="l1", source_file_id="fc-old", target_format="obj",
                           operation_type="convert", status="completed",
                           error_message=None, result_file_id="r1")
        db.get.side_effect = [None, legacy]  # meta returns None, legacy returns
        r = asyncio.get_event_loop().run_until_complete(get_conversion_status("l1", db))
        assert r.id == "l1"
        assert r.result_file_id == "r1"


class TestProcessEndpointStats:
    def test_accurate_succeeded_and_failed(self):
        """Fix 3: stats reflect actual job.status after execution"""
        from yuantus.meta_engine.web.file_router import process_conversion_queue
        import asyncio
        db = MagicMock()
        j1 = MagicMock(); j1.status = "completed"
        j2 = MagicMock(); j2.status = "failed"
        call = [0]
        def poll(wid):
            call[0] += 1
            return [j1, j2, None][call[0]-1]
        with patch("yuantus.meta_engine.web.file_router.JobService") as JS, \
             patch("yuantus.meta_engine.services.job_worker.JobWorker"):
            JS.return_value.poll_next_job.side_effect = poll
            db.refresh = MagicMock()
            r = asyncio.get_event_loop().run_until_complete(
                process_conversion_queue(batch_size=5, db=db)
            )
        assert r["processed"] == 2
        assert r["succeeded"] == 1
        assert r["failed"] == 1
