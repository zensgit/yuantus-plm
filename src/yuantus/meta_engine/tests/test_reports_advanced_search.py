from types import SimpleNamespace
from unittest.mock import MagicMock

from yuantus.meta_engine.reports.models import SavedSearch
from yuantus.meta_engine.reports.report_service import ReportDefinitionService
from yuantus.meta_engine.reports.search_service import AdvancedSearchService, SavedSearchService


class _ItemQuery:
    def __init__(self, items):
        self._items = items

    def count(self):
        return len(self._items)

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def offset(self, _offset):
        return self

    def limit(self, _limit):
        return self

    def all(self):
        return self._items


def _search_session_with_items(items):
    session = MagicMock()
    session.query.return_value = _ItemQuery(items)
    return session


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


def test_advanced_search_resolves_localized_fields_for_report_language():
    item = SimpleNamespace(
        id="item-1",
        config_id="P-001",
        item_type_id="Part",
        generation=1,
        state="Released",
        is_current=True,
        created_at=None,
        properties={
            "name": "Bolt",
            "name_i18n": {"zh_CN": "Bolt CN"},
            "description": "Hex bolt",
            "description_i18n": {"en_US": "Hex bolt", "zh_CN": "Hex bolt CN"},
            "weight": 1.25,
        },
    )
    service = AdvancedSearchService(_search_session_with_items([item]))

    result = service.search(
        columns=["name", "description", "weight"],
        lang="zh_CN",
        fallback_langs=["en_US"],
    )

    row = result["items"][0]
    assert row["name"] == "Bolt CN"
    assert row["description"] == "Hex bolt CN"
    assert row["weight"] == 1.25


def test_advanced_search_localized_fields_can_be_narrowed():
    item = SimpleNamespace(
        id="item-1",
        config_id="P-001",
        item_type_id="Part",
        generation=1,
        state="Released",
        is_current=True,
        created_at=None,
        properties={
            "name": "Bolt",
            "name_i18n": {"zh_CN": "Bolt CN"},
            "description": "Hex bolt",
            "description_i18n": {"zh_CN": "Hex bolt CN"},
        },
    )
    service = AdvancedSearchService(_search_session_with_items([item]))

    result = service.search(
        columns=["name", "description"],
        lang="zh_CN",
        localized_fields=["description"],
    )

    row = result["items"][0]
    assert row["name"] == "Bolt"
    assert row["description"] == "Hex bolt CN"


def test_advanced_search_does_not_add_unrequested_localized_columns():
    item = SimpleNamespace(
        id="item-1",
        config_id="P-001",
        item_type_id="Part",
        generation=1,
        state="Released",
        is_current=True,
        created_at=None,
        properties={
            "name": "Bolt",
            "name_i18n": {"zh_CN": "Bolt CN"},
            "description": "Hex bolt",
            "description_i18n": {"zh_CN": "Hex bolt CN"},
            "weight": 1.25,
        },
    )
    service = AdvancedSearchService(_search_session_with_items([item]))

    result = service.search(columns=["weight"], lang="zh_CN")

    row = result["items"][0]
    assert row["weight"] == 1.25
    assert "name" not in row
    assert "description" not in row


def test_advanced_search_adds_requested_column_from_i18n_sidecar():
    item = SimpleNamespace(
        id="item-1",
        config_id="P-001",
        item_type_id="Part",
        generation=1,
        state="Released",
        is_current=True,
        created_at=None,
        properties={"description_i18n": {"zh_CN": "Hex bolt CN"}},
    )
    service = AdvancedSearchService(_search_session_with_items([item]))

    result = service.search(columns=["description"], lang="zh_CN")

    assert result["items"][0]["description"] == "Hex bolt CN"


def test_report_definition_query_data_source_passes_language_selection():
    service = ReportDefinitionService(MagicMock())
    service.search_service.search = MagicMock(return_value={"items": []})
    report = SimpleNamespace(
        data_source={
            "type": "query",
            "item_type_id": "Part",
            "columns": ["name", "description"],
            "lang": "zh_CN",
            "fallback_langs": ["en_US"],
            "localized_fields": ["description"],
        },
    )

    result = service._execute_data_source(report, parameters=None, page=1, page_size=50)

    assert result == {"items": []}
    service.search_service.search.assert_called_once_with(
        item_type_id="Part",
        filters=None,
        full_text=None,
        sort=None,
        columns=["name", "description"],
        lang="zh_CN",
        fallback_langs=["en_US"],
        localized_fields=["description"],
        page=1,
        page_size=50,
        include_count=True,
    )


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
