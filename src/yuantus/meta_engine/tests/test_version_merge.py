import pytest
from unittest.mock import MagicMock
from yuantus.meta_engine.version.service import VersionService
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.service import VersionError


class TestVersionMerge:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    def test_merge_branch(self, mock_session):
        service = VersionService(mock_session)
        service.file_version_service.get_blocking_file_locks = MagicMock(
            return_value=[]
        )

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
            checked_out_by_id=1,
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

    def test_merge_branch_requires_target_checked_out_by_user(self, mock_session):
        service = VersionService(mock_session)
        service.file_version_service.get_blocking_file_locks = MagicMock(
            return_value=[]
        )

        item = Item(id="item1", current_version_id="ver_main")
        v_main = ItemVersion(
            id="ver_main",
            item_id="item1",
            generation=1,
            revision="A",
            version_label="1.A",
            is_current=True,
            checked_out_by_id=None,
            properties={"color": "red"},
        )
        v_branch = ItemVersion(
            id="ver_branch",
            item_id="item1",
            generation=1,
            revision="A",
            version_label="1.A-dev",
            branch_name="dev",
            properties={"color": "blue"},
        )

        def get_ver(id):
            if id == "ver_main":
                return v_main
            if id == "ver_branch":
                return v_branch
            if id == "item1":
                return item
            return None

        mock_session.query.return_value.get.side_effect = get_ver

        with pytest.raises(
            VersionError, match="Target version ver_main is not checked out by you"
        ):
            service.merge_branch("item1", "ver_branch", "ver_main", user_id=1)

    def test_merge_branch_rejects_foreign_source_file_locks(self, mock_session):
        service = VersionService(mock_session)

        item = Item(id="item1", current_version_id="ver_main")
        v_main = ItemVersion(
            id="ver_main",
            item_id="item1",
            generation=1,
            revision="A",
            version_label="1.A",
            is_current=True,
            checked_out_by_id=1,
            properties={"color": "red"},
        )
        v_branch = ItemVersion(
            id="ver_branch",
            item_id="item1",
            generation=1,
            revision="A",
            version_label="1.A-dev",
            branch_name="dev",
            properties={"color": "blue"},
        )

        def get_ver(id):
            if id == "ver_main":
                return v_main
            if id == "ver_branch":
                return v_branch
            if id == "item1":
                return item
            return None

        mock_session.query.return_value.get.side_effect = get_ver
        service.file_version_service.get_blocking_file_locks = MagicMock(
            side_effect=lambda version_id, user_id=None: [
                MagicMock(checked_out_by_id=9)
            ]
            if version_id == "ver_branch"
            else []
        )

        with pytest.raises(
            VersionError,
            match="Source version has file-level locks held by another user",
        ):
            service.merge_branch("item1", "ver_branch", "ver_main", user_id=1)

    def test_merge_branch_rejects_foreign_target_file_locks(self, mock_session):
        service = VersionService(mock_session)

        item = Item(id="item1", current_version_id="ver_main")
        v_main = ItemVersion(
            id="ver_main",
            item_id="item1",
            generation=1,
            revision="A",
            version_label="1.A",
            is_current=True,
            checked_out_by_id=1,
            properties={"color": "red"},
        )
        v_branch = ItemVersion(
            id="ver_branch",
            item_id="item1",
            generation=1,
            revision="A",
            version_label="1.A-dev",
            branch_name="dev",
            properties={"color": "blue"},
        )

        def get_ver(id):
            if id == "ver_main":
                return v_main
            if id == "ver_branch":
                return v_branch
            if id == "item1":
                return item
            return None

        mock_session.query.return_value.get.side_effect = get_ver
        service.file_version_service.get_blocking_file_locks = MagicMock(
            side_effect=lambda version_id, user_id=None: [
                MagicMock(checked_out_by_id=9)
            ]
            if version_id == "ver_main"
            else []
        )

        with pytest.raises(
            VersionError,
            match="Target version has file-level locks held by another user",
        ):
            service.merge_branch("item1", "ver_branch", "ver_main", user_id=1)
