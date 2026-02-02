from unittest.mock import MagicMock

from yuantus.meta_engine.reports.models import SavedSearch
from yuantus.meta_engine.reports.search_service import SavedSearchService


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
