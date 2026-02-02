from unittest.mock import MagicMock

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
