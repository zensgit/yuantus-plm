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


def test_get_audit_summary_aggregates_counts():
    session = MagicMock()
    service = ElectronicSignatureService(session, secret_key="secret")

    count_q = MagicMock()
    count_q.filter.return_value = count_q
    count_q.scalar.return_value = 3

    by_action_q = MagicMock()
    by_action_q.filter.return_value = by_action_q
    by_action_q.group_by.return_value = by_action_q
    by_action_q.all.return_value = [("sign", 2), ("verify", 1)]

    by_success_q = MagicMock()
    by_success_q.filter.return_value = by_success_q
    by_success_q.group_by.return_value = by_success_q
    by_success_q.all.return_value = [(True, 3)]

    session.query.side_effect = [count_q, by_action_q, by_success_q]

    summary = service.get_audit_summary()

    assert summary["total"] == 3
    assert summary["by_action"]["sign"] == 2
    assert summary["by_action"]["verify"] == 1
    assert summary["by_success"]["true"] == 3


def test_export_audit_logs_supports_json_and_csv():
    from datetime import datetime
    from types import SimpleNamespace

    session = MagicMock()
    service = ElectronicSignatureService(session, secret_key="secret")

    log = SimpleNamespace(
        id="log-1",
        action="sign",
        signature_id="sig-1",
        item_id="item-1",
        actor_id=1,
        actor_username="admin",
        details={"meaning": "approved"},
        success=True,
        error_message=None,
        timestamp=datetime(2026, 2, 6, 12, 0, 0),
        client_ip="127.0.0.1",
    )
    service.list_audit_logs = MagicMock(return_value=[log])

    json_result = service.export_audit_logs(export_format="json")
    assert json_result["extension"] == "json"
    assert json_result["media_type"] == "application/json"
    assert b"items" in json_result["content"]

    csv_result = service.export_audit_logs(export_format="csv")
    assert csv_result["extension"] == "csv"
    assert csv_result["media_type"] == "text/csv"
    text = csv_result["content"].decode("utf-8-sig")
    assert "action" in text
    assert "sign" in text


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
