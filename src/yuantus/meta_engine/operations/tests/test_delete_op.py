import sys
from unittest.mock import MagicMock
sys.modules["psycopg2"] = MagicMock()
sys.modules["yuantus.meta_engine.models.item"] = MagicMock()
sys.modules["yuantus.meta_engine.models.meta_schema"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock()

import unittest
from yuantus.meta_engine.operations.delete_op import DeleteOperation
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem

class TestDeleteOperation(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.mock_session = self.mock_engine.session
        self.mock_perm = self.mock_engine.permission_service
        
        self.mock_engine.user_id = "1"
        self.op = DeleteOperation(self.mock_engine)

    def test_delete_success(self):
        mock_item_type = MagicMock()
        mock_item_type.id = "Part"
        
        aml = GenericItem(id="item-1", type="Part", action=AMLAction.delete)
        
        mock_item = MagicMock()
        mock_item.id = "item-1"
        mock_item.item_type_id = "Part"
        
        self.mock_session.get.return_value = mock_item
        self.mock_perm.check_permission.return_value = True
        
        result = self.op.execute(mock_item_type, aml)
        
        self.mock_session.delete.assert_called_with(mock_item)
        self.assertEqual(result["status"], "deleted")

if __name__ == '__main__':
    unittest.main()
