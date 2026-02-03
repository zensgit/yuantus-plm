from unittest.mock import MagicMock

from yuantus.meta_engine.esign.models import SigningReason
from yuantus.meta_engine.esign.service import ElectronicSignatureService


def test_list_audit_logs_filters():
    session = MagicMock()
    service = ElectronicSignatureService(session, secret_key="secret")

    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.all.return_value = [MagicMock()]
    session.query.return_value = query

    logs = service.list_audit_logs(item_id="item-1", action="sign", limit=10, offset=5)

    assert len(logs) == 1
    session.query.assert_called()
    query.offset.assert_called_with(5)
    query.limit.assert_called_with(10)


def test_update_signing_reason_updates_fields():
    session = MagicMock()
    service = ElectronicSignatureService(session, secret_key="secret")

    reason = SigningReason(
        id="reason-1",
        code="APPROVE",
        name="Approve",
        meaning="approved",
        requires_password=True,
        requires_comment=False,
        is_active=True,
    )
    session.get.return_value = reason

    updated = service.update_signing_reason(
        "reason-1",
        name="Approved",
        requires_comment=True,
        is_active=False,
    )

    assert updated.name == "Approved"
    assert updated.requires_comment is True
    assert updated.is_active is False
    session.add.assert_called_with(reason)
    session.commit.assert_called()
