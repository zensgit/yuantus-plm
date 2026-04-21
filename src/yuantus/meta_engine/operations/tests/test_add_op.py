from unittest.mock import MagicMock

import unittest
# Import the class under test
# Note: we must import it AFTER mocking the modules it depends on
from yuantus.meta_engine.operations.add_op import AddOperation
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem

from unittest.mock import MagicMock, patch

class TestAddOperation(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.mock_session = self.mock_engine.session
        self.mock_perm = self.mock_engine.permission_service
        self.mock_validator = self.mock_engine.validator
        
        self.mock_engine.user_id = "1"
        self.mock_engine.roles = ["admin"]
        
        self.op = AddOperation(self.mock_engine)

    @patch('yuantus.meta_engine.operations.add_op.Item')
    def test_execute_success(self, MockItemClass):
        # Arrange
        mock_item_type = MagicMock()
        mock_item_type.id = "Part"
        mock_item_type.is_relationship = False
        mock_item_type.permission_id = "perm1"
        mock_item_type.on_before_add_method_id = None
        
        aml = GenericItem(
            type="Part",
            action=AMLAction.add,
            properties={"item_number": "P-100", "name": "Screw"}
        )
        
        self.mock_perm.check_permission.return_value = True
        self.mock_validator.validate_and_normalize.return_value = {
            "item_number": "P-100", "name": "Screw"
        }
        
        # Configure the Mock Item instance
        mock_new_item = MagicMock()
        mock_new_item.id = "valid-uuid-string"
        mock_new_item.properties = dict(aml.properties)
        MockItemClass.return_value = mock_new_item
        
        # Act
        result = self.op.execute(mock_item_type, aml)
        
        # Assert (rest same as before)
        self.mock_perm.check_permission.assert_called_with(
            "Part", AMLAction.add, "1", ["admin"]
        )
        
        MockItemClass.assert_called_once()
        self.mock_validator.validate_and_normalize.assert_called()
        self.mock_session.add.assert_called_with(mock_new_item)
        self.mock_engine.lifecycle.attach_lifecycle.assert_called_with(mock_item_type, mock_new_item)
        
        self.assertEqual(result["status"], "created")
        self.assertEqual(result["type"], "Part")

    @patch("yuantus.meta_engine.operations.add_op.apply_auto_numbering")
    @patch("yuantus.meta_engine.operations.add_op.Item")
    def test_execute_routes_properties_through_auto_numbering(self, MockItemClass, numbering_fn):
        mock_item_type = MagicMock()
        mock_item_type.id = "Part"
        mock_item_type.is_relationship = False
        mock_item_type.permission_id = "perm1"
        mock_item_type.on_before_add_method_id = None

        aml = GenericItem(
            type="Part",
            action=AMLAction.add,
            properties={"name": "Washer"},
        )

        self.mock_perm.check_permission.return_value = True
        numbering_fn.return_value = {"item_number": "PART-000001", "number": "PART-000001", "name": "Washer"}
        self.mock_validator.validate_and_normalize.return_value = numbering_fn.return_value

        mock_new_item = MagicMock()
        mock_new_item.id = "valid-uuid-string"
        mock_new_item.properties = dict(aml.properties)
        MockItemClass.return_value = mock_new_item

        self.op.execute(mock_item_type, aml)

        numbering_fn.assert_called_once()
        self.assertEqual(mock_new_item.properties["item_number"], "PART-000001")
        self.assertEqual(mock_new_item.properties["number"], "PART-000001")

    @patch("yuantus.meta_engine.operations.add_op.assert_not_suspended")
    @patch("yuantus.meta_engine.operations.add_op.assert_latest_released")
    @patch("yuantus.meta_engine.operations.add_op.apply_auto_numbering")
    @patch("yuantus.meta_engine.operations.add_op.Item")
    def test_execute_guards_part_bom_relationship_target(self, MockItemClass, numbering_fn, guard_fn, suspended_fn):
        mock_item_type = MagicMock()
        mock_item_type.id = "Part BOM"
        mock_item_type.is_relationship = True
        mock_item_type.permission_id = "perm1"
        mock_item_type.on_before_add_method_id = None

        parent_item = MagicMock(id="parent-1")
        aml = GenericItem(
            type="Part BOM",
            action=AMLAction.add,
            properties={"related_id": "child-1", "quantity": 1},
        )

        self.mock_perm.check_permission.return_value = True
        numbering_fn.return_value = {"related_id": "child-1", "quantity": 1}
        self.mock_validator.validate_and_normalize.return_value = numbering_fn.return_value

        mock_new_item = MagicMock()
        mock_new_item.id = "rel-1"
        mock_new_item.properties = dict(aml.properties)
        mock_new_item.related_id = "child-1"
        MockItemClass.return_value = mock_new_item

        self.op.execute(mock_item_type, aml, parent_item=parent_item)

        guard_fn.assert_called_once_with(self.mock_session, "child-1", context="bom_child")
        suspended_fn.assert_called_once_with(self.mock_session, "child-1", context="bom_child")

    @patch("yuantus.meta_engine.operations.add_op.assert_not_suspended")
    @patch("yuantus.meta_engine.operations.add_op.assert_latest_released")
    @patch("yuantus.meta_engine.operations.add_op.apply_auto_numbering")
    @patch("yuantus.meta_engine.operations.add_op.Item")
    def test_execute_guards_substitute_relationship_target(self, MockItemClass, numbering_fn, guard_fn, suspended_fn):
        mock_item_type = MagicMock()
        mock_item_type.id = "Part BOM Substitute"
        mock_item_type.is_relationship = True
        mock_item_type.permission_id = "perm1"
        mock_item_type.on_before_add_method_id = None

        parent_item = MagicMock(id="bom-1")
        aml = GenericItem(
            type="Part BOM Substitute",
            action=AMLAction.add,
            properties={"related_id": "sub-1"},
        )

        self.mock_perm.check_permission.return_value = True
        numbering_fn.return_value = {"related_id": "sub-1"}
        self.mock_validator.validate_and_normalize.return_value = numbering_fn.return_value

        mock_new_item = MagicMock()
        mock_new_item.id = "rel-2"
        mock_new_item.properties = dict(aml.properties)
        mock_new_item.related_id = "sub-1"
        MockItemClass.return_value = mock_new_item

        self.op.execute(mock_item_type, aml, parent_item=parent_item)

        guard_fn.assert_called_once_with(self.mock_session, "sub-1", context="substitute")
        suspended_fn.assert_called_once_with(self.mock_session, "sub-1", context="substitute")

    @patch("yuantus.meta_engine.operations.add_op.assert_not_suspended")
    @patch("yuantus.meta_engine.operations.add_op.assert_latest_released")
    @patch("yuantus.meta_engine.operations.add_op.apply_auto_numbering")
    @patch("yuantus.meta_engine.operations.add_op.Item")
    def test_execute_suspended_guard_runs_before_auto_numbering(self, MockItemClass, numbering_fn, guard_fn, suspended_fn):
        from yuantus.meta_engine.services.suspended_guard import SuspendedStateError

        mock_item_type = MagicMock()
        mock_item_type.id = "Part BOM"
        mock_item_type.is_relationship = True
        mock_item_type.permission_id = "perm1"
        mock_item_type.on_before_add_method_id = None

        parent_item = MagicMock(id="parent-1")
        aml = GenericItem(
            type="Part BOM",
            action=AMLAction.add,
            properties={"related_id": "child-1", "quantity": 1},
        )

        self.mock_perm.check_permission.return_value = True
        suspended_fn.side_effect = SuspendedStateError(
            reason="target_suspended", target_id="child-1"
        )

        mock_new_item = MagicMock()
        mock_new_item.id = "rel-1"
        mock_new_item.properties = dict(aml.properties)
        mock_new_item.related_id = "child-1"
        MockItemClass.return_value = mock_new_item

        with self.assertRaises(SuspendedStateError):
            self.op.execute(mock_item_type, aml, parent_item=parent_item)

        guard_fn.assert_called_once_with(self.mock_session, "child-1", context="bom_child")
        suspended_fn.assert_called_once_with(self.mock_session, "child-1", context="bom_child")
        numbering_fn.assert_not_called()

if __name__ == '__main__':
    unittest.main()
