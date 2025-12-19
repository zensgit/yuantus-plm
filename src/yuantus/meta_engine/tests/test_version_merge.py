import pytest
from unittest.mock import MagicMock
from yuantus.meta_engine.version.service import VersionService
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.models.item import Item


class TestVersionMerge:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    def test_merge_branch(self, mock_session):
        service = VersionService(mock_session)

        # Setup Item
        item = Item(id="item1", current_version_id="ver_main")
        mock_session.query.return_value.get.side_effect = lambda x: (
            item if x == "item1" else None
        )

        # Setup Versions
        # Mainline: ver_main (Generation 1, Revision A)
        v_main = ItemVersion(
            id="ver_main",
            item_id="item1",
            generation=1,
            revision="A",
            version_label="1.A",
            is_current=True,
            properties={"color": "red"},
        )

        # Branch: ver_branch (Generation 1, Revision A, Branch 'dev')
        v_branch = ItemVersion(
            id="ver_branch",
            item_id="item1",
            generation=1,
            revision="A",
            version_label="1.A-dev",
            branch_name="dev",
            properties={"color": "blue", "size": 10},
        )

        def get_ver(id):
            if id == "ver_main":
                return v_main
            if id == "ver_branch":
                return v_branch
            if id == "item1":
                return item  # for item lookup inside merge
            return None

        mock_session.query.return_value.get.side_effect = get_ver

        # ACT
        merged = service.merge_branch("item1", "ver_branch", "ver_main", user_id=1)

        # ASSERT
        assert merged is not None
        assert merged.generation == 1
        assert merged.revision == "B"  # Next revision of main
        assert merged.version_label == "1.B"
        assert merged.properties["color"] == "blue"  # From branch
        assert merged.properties["size"] == 10  # From branch
        assert not v_main.is_current
        assert merged.is_current is True
        assert item.current_version_id == merged.id

        mock_session.add.assert_any_call(merged)
        mock_session.add.assert_any_call(v_main)
