from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

from yuantus.meta_engine.approvals.models import ApprovalRequest


def test_approval_request_properties_compile_as_json_on_sqlite() -> None:
    rendered = ApprovalRequest.__table__.c.properties.type.compile(
        dialect=sqlite_dialect()
    )

    assert rendered == "JSON"
