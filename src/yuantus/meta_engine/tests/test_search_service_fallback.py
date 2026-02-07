from unittest.mock import MagicMock

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.search_service import SearchService


def test_search_falls_back_to_db_when_client_disabled():
    session = MagicMock()
    service = SearchService(session)
    service.client = None  # force fallback path

    item1 = Item(
        id="item-1",
        item_type_id="Part",
        config_id="P-001",
        generation=1,
        state="released",
        is_current=True,
        properties={"name": "Part 1"},
    )
    item2 = Item(
        id="item-2",
        item_type_id="Part",
        config_id="P-002",
        generation=1,
        state="released",
        is_current=True,
        properties={"name": "Part 2"},
    )

    count_result = MagicMock()
    count_result.scalar.return_value = 2

    items_result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = [item1, item2]
    items_result.scalars.return_value = scalars

    session.execute.side_effect = [count_result, items_result]

    out = service.search("P-00", filters={"state": "released"}, limit=10)

    assert out["total"] == 2
    assert len(out["hits"]) == 2
    assert out["hits"][0]["id"] == "item-1"


def test_reindex_items_returns_db_fallback_note_when_client_disabled():
    session = MagicMock()
    service = SearchService(session)
    service.client = None

    count_result = MagicMock()
    count_result.scalar.return_value = 7
    session.execute.return_value = count_result

    out = service.reindex_items(item_type_id="Part", reset=True, limit=None, batch_size=50)

    assert out["ok"] is True
    assert out["engine"] == "db"
    assert out["indexed"] == 7
    assert out["note"] == "db-fallback"

