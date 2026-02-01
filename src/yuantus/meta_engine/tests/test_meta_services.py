import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from yuantus.meta_engine.services.meta_schema_service import MetaSchemaService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.meta_engine.models.meta_schema import ItemType, Property
from yuantus.meta_engine.permission.models import Access
from yuantus.meta_engine.lifecycle.models import (
    LifecycleState,
    StateIdentityPermission,
)
from yuantus.meta_engine.schemas.aml import AMLAction


class TestMetaSchemaService:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=Session)

    def test_get_json_schema_cached(self, mock_session):
        service = MetaSchemaService(mock_session)

        # Setup ItemType with cached schema
        mock_item_type = ItemType(id="Part", properties_schema={"type": "cached"})
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )

        schema = service.get_json_schema("Part")
        assert schema == {"type": "cached"}

    def test_get_json_schema_generation(self, mock_session):
        service = MetaSchemaService(mock_session)

        # Setup ItemType without cached schema but with properties
        mock_prop = Property(
            name="weight",
            label="Weight",
            data_type="float",
            length=None,
            is_required=True,
            default_value=None,
        )
        mock_item_type = ItemType(
            id="Part", label="Part Item", description="A Part", properties=[mock_prop]
        )
        mock_item_type.properties_schema = None

        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )

        schema = service.get_json_schema("Part")

        assert schema["type"] == "object"
        assert "weight" in schema["properties"]
        assert schema["properties"]["weight"]["type"] == "number"
        assert "weight" in schema["required"]

    def test_get_etag(self, mock_session):
        service = MetaSchemaService(mock_session)
        mock_item_type = ItemType(id="Part", properties_schema={"type": "object"})
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )

        etag = service.get_schema_etag("Part")
        assert len(etag) == 32  # MD5 length

    def test_invalidate_cache(self, mock_session):
        service = MetaSchemaService(mock_session)
        mock_item_type = MagicMock(spec=ItemType)
        # Have to mock attributes on the instance
        mock_item_type.properties_schema = {"some": "schema"}

        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )

        service.invalidate_cache("Part")

        assert mock_item_type.properties_schema is None
        mock_session.add.assert_called_with(mock_item_type)
        mock_session.commit.assert_called_once()


class TestMetaPermissionService:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=Session)

    def test_check_acl_permission_allowed(self, mock_session):
        service = MetaPermissionService(mock_session)

        # Mock ItemType having a permission set
        mock_item_type = ItemType(id="Part", permission_id="perm1")
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )

        # Mock Access entry
        mock_access = Access(
            identity_id="engineer", can_create=True, permission_id="perm1"
        )
        # When querying Access, return list
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_access
        ]

        # User has role 'engineer'
        allowed = service.check_permission(
            item_type_id="Part",
            action=AMLAction.add,
            user_id="user1",
            user_roles=["engineer"],
        )
        assert allowed is True

    def test_check_acl_permission_denied(self, mock_session):
        service = MetaPermissionService(mock_session)

        mock_item_type = ItemType(id="Part", permission_id="perm1")
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )

        # Access only for engineer
        mock_access = Access(
            identity_id="engineer", can_create=True, permission_id="perm1"
        )
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_access
        ]

        # User is 'guest', not 'engineer'
        allowed = service.check_permission(
            item_type_id="Part",
            action=AMLAction.add,
            user_id="user1",
            user_roles=["guest"],
        )
        assert allowed is False

    def test_check_state_permission_override(self, mock_session):
        service = MetaPermissionService(mock_session)

        # Identify state permissions
        # Mock finding state
        mock_state = LifecycleState(name="Draft", permission_id="perm_draft")
        # Mock StateIdentityPermission attached to the state
        state_perm = StateIdentityPermission(
            identity_type="role", identity_value="engineer", can_update=True
        )
        mock_state.identity_permissions = [state_perm]

        mock_item_type = ItemType(id="Part", lifecycle_map_id="lc-1", permission_id=None)

        item_type_query = MagicMock()
        item_type_query.filter.return_value.first.return_value = mock_item_type

        state_query = MagicMock()
        state_query.filter.return_value.filter.return_value.first.return_value = (
            mock_state
        )

        access_query = MagicMock()
        access_query.filter.return_value.all.return_value = []

        mock_session.query.side_effect = [item_type_query, state_query, access_query]

        # engineer can update in Draft
        allowed = service.check_permission(
            item_type_id="Part",
            action=AMLAction.update,
            user_id="user1",
            user_roles=["engineer"],
            item_state="Draft",
        )
        assert allowed is True

    def test_dynamic_creator_permission(self, mock_session):
        service = MetaPermissionService(mock_session)

        mock_item_type = ItemType(id="Part", permission_id="perm_dynamic")
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_item_type
        )

        # Access entry with "Creator" identity
        mock_access = Access(
            identity_id="Creator", can_update=True, permission_id="perm_dynamic"
        )
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_access
        ]

        # User is the creator
        allowed = service.check_permission(
            item_type_id="Part",
            action=AMLAction.update,
            user_id="user1",
            user_roles=[],
            item_state=None,
            item_owner_id="user1",
        )
        assert allowed is True

        # User is NOT the creator
        allowed_not_owner = service.check_permission(
            item_type_id="Part",
            action=AMLAction.update,
            user_id="user2",
            user_roles=[],
            item_state=None,
            item_owner_id="user1",
        )
        assert allowed_not_owner is False
