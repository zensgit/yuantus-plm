from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Repository root not found")


def _load_schema(name: str) -> dict:
    schema_path = _repo_root() / "contracts" / name
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_dedupcad_vision_search_schema() -> None:
    schema = _load_schema("dedupcad_vision_search_v2.schema.json")
    sample = {
        "success": True,
        "total_matches": 1,
        "duplicates": [
            {
                "drawing_id": "d1",
                "file_hash": "abc123",
                "file_name": "drawing_a.dwg",
                "similarity": 0.98,
                "confidence": 0.95,
                "match_level": 2,
                "verdict": "duplicate",
                "levels": {},
            }
        ],
        "similar": [],
        "final_level": 2,
        "timing": {"total_ms": 120.5},
        "level_stats": {},
        "warnings": [],
        "error": None,
    }
    validate(instance=sample, schema=schema)


def test_cad_ml_vision_analyze_schema() -> None:
    schema = _load_schema("cad_ml_vision_analyze.schema.json")
    sample = {
        "success": True,
        "description": {
            "summary": "Mechanical part with cylindrical features",
            "details": ["Main diameter: 20mm"],
            "confidence": 0.9,
        },
        "ocr": None,
        "provider": "stub",
        "processing_time_ms": 123.4,
        "error": None,
        "code": None,
    }
    validate(instance=sample, schema=schema)


def test_cad_extractor_extract_schema() -> None:
    schema = _load_schema("cad_extractor_extract.schema.json")
    sample = {
        "ok": True,
        "attributes": {
            "part_number": "HC-001",
            "description": "Haochen CAD Part",
            "revision": "A",
        },
        "provider": "stub",
        "processing_time_ms": 45.2,
        "error": None,
        "code": None,
    }
    validate(instance=sample, schema=schema)


def test_cad_connector_convert_schema() -> None:
    schema = _load_schema("cad_connector_convert.schema.json")
    sample = {
        "ok": True,
        "job_id": None,
        "artifacts": {
            "geometry": {
                "gltf_url": "https://example.com/mesh.gltf",
                "bin_url": "https://example.com/mesh.bin",
                "bbox": [0, 0, 0, 1, 1, 1],
            },
            "preview": {"png_url": "https://example.com/preview.png"},
            "attributes": {"part_number": "P-1001", "revision": "A"},
            "bom": {"nodes": [], "edges": []},
        },
        "error": None,
        "code": None,
    }
    validate(instance=sample, schema=schema)
