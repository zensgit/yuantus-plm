"""ECM-P1C: the Null publication adapter + registry.

The Null adapter reads the FLAT ECM snapshot shape (not erp's nested item/version),
validates the full per-file identity 5-tuple, and returns a PER-FILE remote_id with
no external I/O. The registry always resolves to Null in P1C (the real Athena CMIS
adapter is P1D-deferred).
"""

from __future__ import annotations

from types import SimpleNamespace

from yuantus.meta_engine.ecm_publication.adapter import (
    EcmPublicationAdapter,
    NullEcmPublicationAdapter,
    SendResult,
    ValidationResult,
)
from yuantus.meta_engine.ecm_publication.adapter_registry import resolve_adapter


def _snapshot(**overrides):
    base = {
        "item_id": "P1",
        "version_id": "v1",
        "file_id": "f1",
        "file_role": "native_cad",
        "target_system": "athena",
        "content_fingerprint_basis": "checksum:c1",
    }
    base.update(overrides)
    return base


def test_null_adapter_is_an_ecm_publication_adapter():
    assert isinstance(NullEcmPublicationAdapter(), EcmPublicationAdapter)


def test_build_payload_reads_flat_snapshot_keys():
    payload = NullEcmPublicationAdapter().build_payload(_snapshot())
    assert payload["item_id"] == "P1"
    assert payload["version_id"] == "v1"
    assert payload["file_id"] == "f1"
    assert payload["file_role"] == "native_cad"
    assert payload["target_system"] == "athena"
    assert payload["snapshot"]["content_fingerprint_basis"] == "checksum:c1"


def test_validate_contract_flags_each_missing_identity_field():
    payload = {"item_id": "P1"}  # everything else missing
    result = NullEcmPublicationAdapter().validate_contract(payload)
    assert isinstance(result, ValidationResult)
    assert result.ok is False
    assert set(result.errors) == {
        "missing version_id",
        "missing file_id",
        "missing file_role",
        "missing target_system",
    }


def test_validate_contract_ok_on_full_identity():
    payload = NullEcmPublicationAdapter().build_payload(_snapshot())
    assert NullEcmPublicationAdapter().validate_contract(payload).ok is True


def test_send_is_ok_with_per_file_remote_id_no_error():
    adapter = NullEcmPublicationAdapter()
    payload = adapter.build_payload(_snapshot())
    result = adapter.send(payload)
    assert isinstance(result, SendResult)
    assert result.ok is True
    assert result.error is None and result.error_kind is None
    assert result.remote_id == "null:P1:v1:f1:native_cad"


def test_send_remote_id_differs_per_file_of_same_version():
    adapter = NullEcmPublicationAdapter()
    a = adapter.send(adapter.build_payload(_snapshot(file_id="f1", file_role="native_cad")))
    b = adapter.send(adapter.build_payload(_snapshot(file_id="f2", file_role="drawing")))
    assert a.remote_id != b.remote_id  # per-file, no collision


def test_resolve_adapter_always_null_in_p1c():
    # default settings
    assert isinstance(resolve_adapter("athena"), NullEcmPublicationAdapter)
    # injected settings (SimpleNamespace tolerated) + unknown target
    injected = SimpleNamespace(SOME_FUTURE_ECM_SETTING="x")
    assert isinstance(
        resolve_adapter("anything", settings=injected), NullEcmPublicationAdapter
    )
    assert isinstance(resolve_adapter(None), NullEcmPublicationAdapter)
