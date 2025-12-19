import sys
from unittest.mock import MagicMock
sys.modules["psycopg2"] = MagicMock()
sys.modules["yuantus.meta_engine.models.item"] = MagicMock()
sys.modules["yuantus.meta_engine.models.meta_schema"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock()

import unittest
from yuantus.meta_engine.operations.update_op import UpdateOperation
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem

class TestUpdateOperation(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.mock_session = self.mock_engine.session
        self.mock_perm = self.mock_engine.permission_service
        self.mock_validator = self.mock_engine.validator
        
        self.mock_engine.user_id = "1"
        self.mock_engine.roles = ["admin"]
        
        self.op = UpdateOperation(self.mock_engine)

    def test_update_success(self):
        # Arrange
        mock_item_type = MagicMock()
        mock_item_type.id = "Part"
        mock_item_type.on_after_update_method_id = None
        
        aml = GenericItem(
            id="item-1",
            type="Part",
            action=AMLAction.update,
            properties={"name": "Updated Name"}
        )
        
        # Mock existing item
        mock_item = MagicMock()
        mock_item.id = "item-1"
        mock_item.item_type_id = "Part"
        mock_item.properties = {"name": "Old Name", "number": "P-100"}
        
        self.mock_session.get.return_value = mock_item
        self.mock_perm.check_permission.return_value = True
        
        # Mock validation result
        self.mock_validator.validate_and_normalize.return_value = {
            "name": "Updated Name", "number": "P-100"
        }
        
        # Act
        result = self.op.execute(mock_item_type, aml)
        
        # Assert
        # Verify db retrieval
        self.mock_session.get.assert_called_with(sys.modules["yuantus.meta_engine.models.item"].Item, "item-1")
        
        # Verify validation called with MERGED properties
        expected_merged = {"name": "Updated Name", "number": "P-100"}
        self.mock_validator.validate_and_normalize.assert_called_with(mock_item_type, expected_merged)
        
        # Verify item properties updated
        self.assertEqual(mock_item.properties["name"], "Updated Name")
        
        self.assertEqual(result["status"], "updated")

if __name__ == '__main__':
    unittest.main()
