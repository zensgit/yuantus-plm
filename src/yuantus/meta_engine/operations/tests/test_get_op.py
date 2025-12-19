import sys
from unittest.mock import MagicMock

# Mock external dependencies
sys.modules["psycopg2"] = MagicMock()
sys.modules["yuantus.meta_engine.models.item"] = MagicMock()
sys.modules["yuantus.meta_engine.models.meta_schema"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock() # Mock sqlalchemy entirely

import unittest
from yuantus.meta_engine.operations.get_op import GetOperation
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem

class TestGetOperation(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.mock_session = self.mock_engine.session
        self.mock_perm = self.mock_engine.permission_service
        
        self.mock_engine.user_id = "1"
        self.mock_engine.roles = ["guest"]
        
        self.op = GetOperation(self.mock_engine)

    def test_get_simple(self):
        # Arrange
        mock_item_type = MagicMock()
        mock_item_type.id = "Part"
        
        aml = GenericItem(type="Part", action=AMLAction.get, properties={})
        
        # Mock DB results
        mock_item_1 = MagicMock()
        mock_item_1.id = "id-1"
        mock_item_1.item_type_id = "Part"
        mock_item_1.state = "Released"
        mock_item_1.properties = {"item_number": "P-100"}
        mock_item_1.created_by_id = None
        
        # Configure session.execute().scalars().all()
        mock_result_proxy = MagicMock()
        mock_scalars = MagicMock()
        mock_result_proxy.scalars.return_value = mock_scalars
        mock_scalars.all.return_value = [mock_item_1]
        self.mock_session.execute.return_value = mock_result_proxy
        
        # Mock permission
        self.mock_perm.check_permission.return_value = True
        
        # Act
        result = self.op.execute(mock_item_type, aml)
        
        # Assert
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["id"], "id-1")
        self.assertEqual(result["items"][0]["properties"]["item_number"], "P-100")
        
    def test_get_with_fields(self):
        # Arrange
        mock_item_type = MagicMock()
        
        # GenericItem usually doesn't have _fields unless injected, but we support injection strategy or subclass
        # The code checks getattr(aml, "_fields", None)
        aml = GenericItem(type="Part", action=AMLAction.get, properties={})
        setattr(aml, "_fields", ["id", "state", "item_number"])
        
        mock_item_1 = MagicMock()
        mock_item_1.id = "id-1"
        mock_item_1.item_type_id = "Part"
        mock_item_1.state = "Draft"
        mock_item_1.properties = {"item_number": "P-200", "desc": "Hidden"}
        
        mock_result_proxy = MagicMock()
        mock_result_proxy.scalars.return_value.all.return_value = [mock_item_1]
        self.mock_session.execute.return_value = mock_result_proxy
        
        self.mock_perm.check_permission.return_value = True
        
        # Act
        result = self.op.execute(mock_item_type, aml)
        
        # Assert
        item_data = result["items"][0]
        # Should have id, state
        self.assertIn("id", item_data)
        self.assertIn("state", item_data)
        # Should have filtered properties containing ONLY item_number
        self.assertEqual(item_data["properties"], {"item_number": "P-200"})
        # Should NOT have 'desc' in properties
        self.assertNotIn("desc", item_data["properties"])

if __name__ == '__main__':
    unittest.main()
