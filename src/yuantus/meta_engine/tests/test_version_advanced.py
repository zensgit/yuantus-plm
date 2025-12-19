import pytest
from unittest.mock import MagicMock
from yuantus.meta_engine.version.service import VersionService
from yuantus.meta_engine.version.models import ItemVersion


class TestVersionAdvanced:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    def test_create_branch(self, mock_session):
        service = VersionService(mock_session)

        # Mock source version
        src = ItemVersion(
            id="v1",
            generation=1,
            revision="A",
            version_label="1.A",
            properties={"color": "red"},
        )
        mock_session.query.return_value.get.return_value = src

        branch = service.create_branch("item1", "v1", "exp", 1)

        assert branch.branch_name == "exp"
        assert branch.version_label == "1.A-exp"
        assert branch.predecessor_id == "v1"
        assert branch.properties == {"color": "red"}
        mock_session.add.assert_called()

    def test_compare_versions(self, mock_session):
        service = VersionService(mock_session)

        v1 = ItemVersion(
            id="v1", version_label="1.A", properties={"color": "red", "size": 10}
        )
        v2 = ItemVersion(
            id="v2", version_label="1.B", properties={"color": "blue", "size": 10}
        )

        def get_mock(x):
            if x == "v1":
                return v1
            if x == "v2":
                return v2
            return None

        mock_session.query.return_value.get.side_effect = get_mock

        res = service.compare_versions("v1", "v2")

        assert "color" in res["diffs"]
        assert res["diffs"]["color"]["a"] == "red"
        assert res["diffs"]["color"]["b"] == "blue"
        assert "size" not in res["diffs"]  # Same value

    def test_get_version_tree(self, mock_session):
        service = VersionService(mock_session)

        v1 = ItemVersion(id="v1", version_label="1.A")
        v2 = ItemVersion(id="v2", version_label="1.B", predecessor_id="v1")

        mock_session.query.return_value.filter_by.return_value.all.return_value = [
            v1,
            v2,
        ]

        tree = service.get_version_tree("item1")
        assert len(tree) == 2
        assert tree[1]["predecessor_id"] == "v1"
