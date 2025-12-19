import pytest
from unittest.mock import MagicMock
from yuantus.meta_engine.lifecycle.service import LifecycleService
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.lifecycle.models import LifecycleState
from yuantus.meta_engine.version.models import ItemVersion

# Import models to ensure Registry is populated for string lookup


class TestLifecycleVersionIntegration:
    @pytest.fixture
    def mock_session(self):
        s = MagicMock()
        return s

    def test_promote_releases_version(self, mock_session):
        service = LifecycleService(mock_session)

        # Setup Item
        item = Item(
            id="item1",
            item_type_id="Part",
            state="Draft",
            current_state="state_draft",
            is_versionable=True,
            current_version_id="ver1",
        )

        # Setup Lifecycle Objects (Mock queries)
        # 1. ItemType (for get_lifecycle_map)
        # Mock session.get(ItemType) -> item_type with lifecycle_map_id
        it = MagicMock()
        it.lifecycle_map_id = "map1"

        # 2. LifecycleMap
        lc_map = MagicMock()
        lc_map.id = "map1"
        lc_map.name = "Part Lifecycle"

        # 3. States
        state_draft = LifecycleState(
            id="state_draft", name="Draft", lifecycle_map_id="map1"
        )
        state_released = LifecycleState(
            id="state_released", name="Released", lifecycle_map_id="map1"
        )

        # 4. Transition
        transition = MagicMock()
        transition.id = "trans1"
        transition.role_allowed_id = None
        transition.condition = None

        # 5. Version
        ver = ItemVersion(
            id="ver1", item_id="item1", is_released=False, state="Draft", properties={}
        )

        # Configure Mock Session Queries
        def get_side_effect(cls, id):
            if cls.__name__ == "ItemType":
                return it
            if cls.__name__ == "LifecycleState":
                if id == "state_draft":
                    return state_draft
                if id == "state_released":
                    return state_released
            if cls.__name__ == "RBACUser":
                return MagicMock(is_superuser=True)
            return None

        mock_session.get.side_effect = get_side_effect

        # Query filters
        # LifecycleMap query
        # LifecycleState query (by name)
        # LifecycleTransition query
        # ItemVersion query (inside VersionService)
        # Item query (inside VersionService)

        def query_side_effect(cls):
            q = MagicMock()
            if cls.__name__ == "LifecycleMap":
                q.filter.return_value.first.return_value = lc_map
            elif cls.__name__ == "LifecycleState":
                # returns query mock that when filtered returns state object
                q.filter.return_value.first.side_effect = [state_draft, state_released]
                # Note: promote calls query for current state (if mismatch) and target state.
                # Logic is complex to mock perfectly with just .return_value chain if called multiple times.

                # Simplified: Assume correct return order or specific checks.
                # promote logic:
                # 1. get current state obj (via get or query)
                # 2. get target state obj (via query)

                # Let's just mock the specific calls.
                pass

            elif cls.__name__ == "LifecycleTransition":
                q.filter.return_value.first.return_value = transition
            elif cls.__name__ == "Item":
                q.filter_by.return_value.one.return_value = item
            elif cls.__name__ == "ItemVersion":
                q.filter_by.return_value.one.return_value = ver
            return q

        mock_session.query.side_effect = query_side_effect

        # We need to ensure state_released.name == "Released" which it is.
        # And make sure query for target state returns it.

        # Refine query mock for States
        # promote calls:
        #   query(LifecycleState).filter(map_id, name==item.state) -> current
        #   query(LifecycleState).filter(map_id, name==target) -> target

        # Creating a specific mock for query(LifecycleState)
        q_state = MagicMock()

        def filter_side_effect(*args):
            # args contain BinaryExpressions. Hard to inspect.
            # But we can return a mock that returns the right thing on .first()
            # This is brittle.
            # Alternative: Rely on the order of calls.
            # 1. Current state query (if item.state used)
            # 2. Target state query

            # Since we passed current_state matches item.current_state ID,
            # promote uses session.get(LifecycleState, item.current_state).
            # So current state comes from get().
            # Only target state comes from query().

            m = MagicMock()
            m.first.return_value = state_released
            return m

        # Hook registry mock to avoid real hooks
        service.hook_registry = MagicMock()
        service.hook_registry.execute.return_value.abort = False

        # Mock Condition Evaluator
        service.condition_evaluator = MagicMock()
        service.condition_evaluator.evaluate.return_value = True

        # Update session query to handle LifecycleState specific behavior
        original_query = mock_session.query

        def smart_query(cls):
            if cls.__name__ == "LifecycleState":
                q = MagicMock()
                q.filter.side_effect = filter_side_effect
                return q
            return original_query(cls)

        mock_session.query = smart_query

        # ACT
        result = service.promote(item, "Released", user_id=1)

        # ASSERT
        assert result.success, f"Promote failed: {result.error}"
        assert item.state == "Released"
        assert ver.is_released is True
        assert ver.state == "Released"
