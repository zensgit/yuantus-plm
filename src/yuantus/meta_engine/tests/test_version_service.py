import pytest
from unittest.mock import MagicMock
from yuantus.meta_engine.version.service import VersionService
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.models import ItemVersion


class TestVersionService:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    def test_create_initial_version(self, mock_session):
        service = VersionService(mock_session)

        # Mock Item
        item = Item(id="item-1", is_versionable=True, properties={})

        # Determine if version exists
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        ver = service.create_initial_version(item, user_id=1)

        assert ver is not None
        assert ver.generation == 1
        assert ver.revision == "A"
        assert ver.is_current is True
        assert item.current_version_id == ver.id

        mock_session.add.assert_called()

    def test_checkout(self, mock_session):
        service = VersionService(mock_session)

        item = Item(id="item-1", current_version_id="ver-1")
        version = ItemVersion(
            id="ver-1",
            item_id="item-1",
            state="Draft",
            is_released=False,
            checked_out_by_id=None,
        )

        # Mock queries
        mock_session.query.return_value.filter_by.side_effect = [
            MagicMock(one=lambda: item),
            MagicMock(one=lambda: version),
        ]

        checked_out = service.checkout("item-1", user_id=2, comment="Edit")

        assert checked_out.checked_out_by_id == 2
        assert checked_out.checked_out_at is not None

    def test_revise(self, mock_session):
        service = VersionService(mock_session)

        item = Item(id="item-1", current_version_id="ver-1")
        current_ver = ItemVersion(
            id="ver-1",
            item_id="item-1",
            generation=1,
            revision="A",
            version_label="1.A",
            is_current=True,
        )

        # Mock queries
        item_query = MagicMock()
        item_query.filter_by.return_value.one.return_value = item

        ver_query = MagicMock()
        ver_query.filter_by.return_value.one.return_value = current_ver

        file_query = MagicMock()
        file_query.filter_by.return_value = file_query
        file_query.all.return_value = []

        mock_session.query.side_effect = [item_query, ver_query, file_query]

        new_ver = service.revise("item-1", user_id=1)

        assert new_ver.generation == 1
        assert new_ver.revision == "B"
        assert new_ver.predecessor_id == "ver-1"
        assert current_ver.is_current is False
        assert item.current_version_id == new_ver.id
