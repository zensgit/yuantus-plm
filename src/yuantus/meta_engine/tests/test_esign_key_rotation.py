from datetime import datetime
import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import MagicMock

from yuantus.meta_engine.esign.models import ElectronicSignature, SignatureStatus
from yuantus.meta_engine.esign.service import ElectronicSignatureService
from yuantus.meta_engine.models.item import Item


def _make_signature(*, secret_key: str, signed_at: datetime) -> SimpleNamespace:
    message = ElectronicSignatureService._build_signature_message(
        item_id="item-1",
        item_generation=1,
        user_id=1,
        meaning="approved",
        content_hash="content-hash",
        timestamp=signed_at,
    )
    signature_hash = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return SimpleNamespace(
        id="sig-1",
        item_id="item-1",
        item_generation=1,
        signer_id=1,
        signer_username="admin",
        signer_full_name="admin",
        meaning="approved",
        signed_at=signed_at,
        status=SignatureStatus.VALID.value,
        content_hash="content-hash",
        signature_hash=signature_hash,
    )


def test_verify_accepts_rotated_secret_keys():
    session = MagicMock()
    signed_at = datetime(2026, 2, 6, 12, 0, 0)

    old_key = "old-secret"
    new_key = "new-secret"

    signature = _make_signature(secret_key=old_key, signed_at=signed_at)

    def _get(model, key):
        if model is ElectronicSignature and key == "sig-1":
            return signature
        if model is Item and key == "item-1":
            return None
        return None

    session.get.side_effect = _get

    service = ElectronicSignatureService(
        session,
        secret_key=new_key,
        verify_secret_keys=[new_key, old_key],
    )
    result = service.verify("sig-1", actor_id=2, actor_username="verifier")

    assert result["is_valid"] is True
    assert result["issues"] == []
    session.commit.assert_called()


def test_verify_audit_log_uses_actor_identity():
    session = MagicMock()
    signed_at = datetime(2026, 2, 6, 12, 0, 0)

    key = "secret"
    signature = _make_signature(secret_key=key, signed_at=signed_at)

    def _get(model, key):
        if model is ElectronicSignature and key == "sig-1":
            return signature
        if model is Item and key == "item-1":
            return None
        return None

    session.get.side_effect = _get

    service = ElectronicSignatureService(
        session,
        secret_key=key,
        verify_secret_keys=[key],
    )
    service.verify("sig-1", actor_id=99, actor_username="checker")

    assert session.add.called
    audit = session.add.call_args.args[0]
    assert audit.action == "verify"
    assert audit.actor_id == 99
    assert audit.actor_username == "checker"

