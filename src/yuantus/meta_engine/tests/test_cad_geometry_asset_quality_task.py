import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.tasks import cad_pipeline_tasks


def test_cad_geometry_persists_connector_asset_quality_metadata():
    session = MagicMock()
    file_container = SimpleNamespace(
        id="file-1",
        filename="assembly.step",
        system_path="/vault/file-1.step",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        geometry_path=None,
        cad_metadata_path=None,
        conversion_status=None,
        conversion_error="old-error",
        get_extension=lambda: "step",
    )
    session.get.return_value = file_container

    connector_payload = {
        "artifacts": {
            "geometry": {
                "gltf_url": "https://converter.example/artifacts/file-1/mesh.gltf",
                "bin_url": "https://converter.example/artifacts/file-1/mesh.bin",
                "bbox": [0, 0, 0, 10, 20, 30],
                "lods": [
                    {
                        "level": 0,
                        "ratio": 1.0,
                        "gltf_url": "https://converter.example/artifacts/file-1/mesh.gltf",
                    },
                    {
                        "level": 1,
                        "ratio": 0.4,
                        "gltf_url": "https://converter.example/artifacts/file-1/mesh-lod1.gltf",
                    },
                ],
            },
            "result": {
                "status": "degraded",
                "error_output": None,
                "warnings": ["lod1 triangle budget exceeded"],
            },
            "mesh_stats": {
                "triangle_count": 420,
                "entity_count": 12,
            },
        }
    }

    download_results = iter(
        [
            "geometry/fi/file-1.gltf",
            "geometry/fi/file-1.bin",
        ]
    )
    file_service = MagicMock()
    file_service.upload_file.return_value = "cad_metadata/fi/file-1.json"

    with patch.object(cad_pipeline_tasks, "_ensure_source_exists"):
        with patch.object(cad_pipeline_tasks, "_cad_connector_enabled", return_value=True):
            with patch.object(
                cad_pipeline_tasks,
                "_call_cad_connector_convert",
                return_value=connector_payload,
            ):
                with patch.object(
                    cad_pipeline_tasks,
                    "_download_artifact",
                    side_effect=lambda *_args, **_kwargs: next(download_results),
                ):
                    with patch.object(
                        cad_pipeline_tasks,
                        "FileService",
                        return_value=file_service,
                    ):
                        result = cad_pipeline_tasks.cad_geometry({"file_id": "file-1"}, session)

    assert result["ok"] is True
    assert result["source"] == "connector"
    assert result["geometry_path"] == "geometry/fi/file-1.gltf"
    assert result["cad_metadata_url"] == "/api/v1/file/file-1/cad_metadata"
    assert file_container.geometry_path == "geometry/fi/file-1.gltf"
    assert file_container.cad_metadata_path == "cad_metadata/fi/file-1.json"
    assert file_container.conversion_error is None

    uploaded_stream = file_service.upload_file.call_args.args[0]
    uploaded_key = file_service.upload_file.call_args.args[1]
    uploaded_payload = json.loads(uploaded_stream.getvalue().decode("utf-8"))

    assert uploaded_key == "cad_metadata/fi/file-1.json"
    assert uploaded_payload["kind"] == "cad_quality"
    assert uploaded_payload["source"] == "connector"
    assert uploaded_payload["bbox"] == [0, 0, 0, 10, 20, 30]
    assert uploaded_payload["lods"][1]["level"] == 1
    assert uploaded_payload["mesh_stats"]["triangle_count"] == 420
    assert uploaded_payload["result"]["status"] == "degraded"
    assert uploaded_payload["result"]["warnings"] == [
        "lod1 triangle budget exceeded"
    ]

