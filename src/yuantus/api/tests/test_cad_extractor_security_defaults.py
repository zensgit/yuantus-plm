from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient


def _load_cad_extractor_module():
    root = Path(__file__).resolve().parents[4]
    module_path = root / "services" / "cad-extractor" / "app.py"
    module_name = f"cad_extractor_app_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_cad_extractor_requires_token_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CAD_EXTRACTOR_AUTH_MODE", raising=False)
    monkeypatch.delenv("CAD_EXTRACTOR_SERVICE_TOKEN", raising=False)
    module = _load_cad_extractor_module()
    client = TestClient(module.app)

    response = client.post(
        "/api/v1/extract",
        files={"file": ("part.step", b"solid data")},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "CAD_EXTRACTOR_SERVICE_TOKEN not configured"


def test_cad_extractor_accepts_configured_service_token(monkeypatch) -> None:
    monkeypatch.delenv("CAD_EXTRACTOR_AUTH_MODE", raising=False)
    monkeypatch.setenv("CAD_EXTRACTOR_SERVICE_TOKEN", "secret-token")
    module = _load_cad_extractor_module()
    client = TestClient(module.app)

    response = client.post(
        "/api/v1/extract",
        files={"file": ("part.step", b"solid data")},
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
