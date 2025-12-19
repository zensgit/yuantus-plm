import sys
from unittest.mock import MagicMock

# Mock external dependencies to avoid SQLAlchemy initialization headaches
sys.modules["psycopg2"] = MagicMock()
sys.modules["yuantus.meta_engine.models.item"] = MagicMock()
sys.modules["yuantus.meta_engine.models.meta_schema"] = MagicMock()

import unittest
import uuid
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

if __name__ == '__main__':
    unittest.main()
