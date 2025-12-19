"""
CAD Service
Handles CAD file attribute extraction and synchronization with Meta Engine Items.
"""

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from yuantus.meta_engine.models.item import Item
from yuantus.exceptions.handlers import ValidationError

logger = logging.getLogger(__name__)


class CadService:
    def __init__(self, session: Session):
        self.session = session

    def extract_attributes(self, file_path: str) -> Dict[str, Any]:
        """
        Simulates extracting attributes from a CAD file.
        In a real system, this would use libraries like ezdxf, Open Cascade, or external APIs.
        """
        logger.info(f"Simulating CAD attribute extraction from {file_path}")

        # Simulate different attributes based on file name for testing
        if "part_a.dwg" in file_path:
            return {
                "part_number": "PA-001",
                "description": "Assembly Part A",
                "material": "Steel",
                "revision": "A",
                "designer": "John Doe",
            }
        elif "part_b.dwg" in file_path:
            return {
                "part_number": "PB-002",
                "description": "Component Part B",
                "material": "Aluminum",
                "revision": "B",
                "weight": 1.5,
            }
        elif "failed.dwg" in file_path:
            logger.warning(f"Simulating failed extraction for {file_path}")
            raise ValueError("Simulated CAD extraction failure: file corrupt")
        else:
            return {
                "part_number": "GEN-001",
                "description": f"Generic CAD Part from {file_path}",
                "material": "Unknown",
            }

    def sync_attributes_to_item(
        self, item_id: str, extracted_attributes: Dict[str, Any], user_id: int
    ) -> Item:
        """
        Synchronizes extracted CAD attributes to an existing Item's properties.
        """
        item = self.session.get(Item, item_id)
        if not item:
            raise ValidationError(f"Item {item_id} not found for attribute sync.")

        current_props = dict(item.properties or {})
        current_props.update(extracted_attributes)
        item.properties = current_props
        item.modified_by_id = user_id  # Update audit trail

        self.session.add(item)
        self.session.commit()  # Commit changes immediately for atomicity

        logger.info(f"Synchronized attributes for Item {item_id} from CAD file.")
        return item
