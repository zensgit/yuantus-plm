import sys
from unittest.mock import MagicMock
sys.modules["psycopg2"] = MagicMock()
sys.modules["yuantus.meta_engine.models.item"] = MagicMock()
sys.modules["yuantus.meta_engine.models.meta_schema"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock()

import unittest
from yuantus.meta_engine.operations.promote_op import PromoteOperation
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem

class TestPromoteOperation(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.mock_session = self.mock_engine.session
        self.mock_perm = self.mock_engine.permission_service
        self.mock_lifecycle = self.mock_engine.lifecycle
        
        self.mock_engine.user_id = "1"
        self.op = PromoteOperation(self.mock_engine)

    def test_promote_success(self):
        mock_item_type = MagicMock()
        mock_item_type.id = "Part"
        
        aml = GenericItem(
            id="item-1",
            type="Part",
            action=AMLAction.promote,
            properties={"target_state": "Released"}
        )
        
        mock_item = MagicMock()
        mock_item.id = "item-1"
        mock_item.item_type_id = "Part"
        mock_item.state = "Draft"
        
        self.mock_session.get.return_value = mock_item
        self.mock_perm.check_permission.return_value = True
        
        # Mock successful lifecycle result
        mock_result = MagicMock()
        mock_result.success = True
        self.mock_lifecycle.promote.return_value = mock_result
        
        # Act
        result = self.op.execute(mock_item_type, aml)
        
        # Assert
        self.mock_lifecycle.promote.assert_called()
        args, kwargs = self.mock_lifecycle.promote.call_args
        self.assertEqual(kwargs['target_state_name'], "Released")
        
        self.mock_session.flush.assert_called()

if __name__ == '__main__':
    unittest.main()
