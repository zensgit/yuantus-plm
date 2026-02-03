from unittest.mock import MagicMock

from yuantus.meta_engine.reports.models import SavedSearch
from yuantus.meta_engine.reports.report_service import ReportDefinitionService
from yuantus.meta_engine.reports.search_service import AdvancedSearchService, SavedSearchService


def test_run_saved_search_updates_usage():
    session = MagicMock()
    service = SavedSearchService(session)

    saved = SavedSearch(
        id="ss-1",
        name="Recent Items",
        criteria={"filters": []},
        page_size=5,
        use_count=0,
    )

    session.get.return_value = saved
    service.search_service.search = MagicMock(return_value={"items": []})

    result = service.run_saved_search("ss-1", page=1, page_size=2)

    assert result == {"items": []}
    assert saved.use_count == 1
    assert saved.last_used_at is not None
    session.add.assert_called_with(saved)
    session.commit.assert_called()


def test_report_export_csv_payload_infers_columns():
    service = ReportDefinitionService(MagicMock())
    data = {"items": [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]}

    content, media_type, extension = service._build_export_payload(data, "csv")

    text = content.decode("utf-8-sig")
    assert "a,b" in text
    assert "1,x" in text
    assert media_type == "text/csv"
    assert extension == "csv"


def test_report_export_json_payload_preserves_structure():
    service = ReportDefinitionService(MagicMock())
    data = {"items": [{"a": 1, "b": "x"}], "total": 1}

    content, media_type, extension = service._build_export_payload(data, "json")

    payload = content.decode("utf-8")
    assert '"items"' in payload
    assert media_type == "application/json"
    assert extension == "json"


def test_advanced_search_supports_prefix_suffix_filters():
    class DummyQuery:
        def __init__(self):
            self.expressions = []

        def filter(self, *expr):
            self.expressions.extend(expr)
            return self

    service = AdvancedSearchService(MagicMock())
    query = DummyQuery()

    service._apply_filter(
        query, {"field": "config_id", "op": "startswith", "value": "ABC"}
    )
    service._apply_filter(query, {"field": "config_id", "op": "endswith", "value": "XYZ"})
    service._apply_filter(
        query, {"field": "config_id", "op": "not_contains", "value": "123"}
    )

    assert len(query.expressions) == 3
