from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from yuantus.meta_engine.web.cad_router import (
    _load_cad_document_payload,
    _load_cad_metadata_payload,
)


def test_load_cad_metadata_payload_downloads_json_via_bytesio() -> None:
    file_container = SimpleNamespace(cad_metadata_path="vault/cad/metadata.json")

    def write_payload(_path, output_stream):
        output_stream.write(b'{"mesh": {"faces": 12}}')

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        file_service_cls.return_value.download_file.side_effect = write_payload

        payload = _load_cad_metadata_payload(file_container)

    assert payload == {"mesh": {"faces": 12}}


def test_load_cad_document_payload_downloads_json_via_bytesio() -> None:
    file_container = SimpleNamespace(cad_document_path="vault/cad/document.json")

    def write_payload(_path, output_stream):
        output_stream.write(b'{"entities": [{"id": 1}]}')

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        file_service_cls.return_value.download_file.side_effect = write_payload

        payload = _load_cad_document_payload(file_container)

    assert payload == {"entities": [{"id": 1}]}
