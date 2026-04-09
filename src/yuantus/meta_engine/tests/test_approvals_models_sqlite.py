from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

from yuantus.meta_engine.approvals.models import ApprovalRequest, ApprovalRequestEvent
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.models.base import Base


def test_approval_request_properties_compile_as_json_on_sqlite() -> None:
    rendered = ApprovalRequest.__table__.c.properties.type.compile(
        dialect=sqlite_dialect()
    )

    assert rendered == "JSON"


def test_approval_request_event_properties_compile_as_json_on_sqlite() -> None:
    rendered = ApprovalRequestEvent.__table__.c.properties.type.compile(
        dialect=sqlite_dialect()
    )

    assert rendered == "JSON"


def test_import_all_models_registers_approval_request_event_table() -> None:
    import_all_models()

    assert "meta_approval_request_events" in Base.metadata.tables
