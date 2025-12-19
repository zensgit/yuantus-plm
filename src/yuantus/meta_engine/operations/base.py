from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING
from yuantus.meta_engine.schemas.aml import GenericItem

if TYPE_CHECKING:
    from ..services.engine import AMLEngine
    from ..models.meta_schema import ItemType

class BaseOperation(ABC):
    """
    Abstract base class for AML operations (Add, Get, Update, etc.)
    """
    def __init__(self, engine: 'AMLEngine'):
        self.engine = engine
        self.session = engine.session
        self.permission_service = engine.permission_service
        self.user_id = engine.user_id
        self.roles = engine.roles

    @abstractmethod
    def execute(self, item_type: 'ItemType', aml: GenericItem) -> Dict[str, Any]:
        pass
