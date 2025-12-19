"""
Search Event Listeners
Syncs Item changes to the Search Engine.
"""

import logging
from typing import Union
from yuantus.database import get_db_session
from yuantus.meta_engine.events.domain_events import (
    ItemCreatedEvent,
    ItemUpdatedEvent,
    ItemDeletedEvent,
    ItemStateChangedEvent,
)
from yuantus.meta_engine.events.event_bus import event_bus
from yuantus.meta_engine.services.search_service import SearchService
from yuantus.meta_engine.models.item import Item

logger = logging.getLogger(__name__)


def sync_item_to_search(
    event: Union[ItemCreatedEvent, ItemUpdatedEvent, ItemStateChangedEvent],
):
    """
    Handler for Item creation/update/state-change events.
    Fetches the latest item state and indexes it.
    """
    logger.info(f"Syncing item {event.item_id} to search index...")

    # We need a new DB session here because event handlers run outside the original transaction scope
    # (or after commit).
    try:
        with get_db_session() as session:
            item = session.get(Item, event.item_id)
            if item:
                search_service = SearchService()
                search_service.index_item(item)
            else:
                logger.warning(f"Item {event.item_id} not found during search sync.")
    except Exception as e:
        logger.error(
            f"Failed to sync item {event.item_id} to search: {e}", exc_info=True
        )


def remove_item_from_search(event: ItemDeletedEvent):
    """Handler for Item deletion events."""
    logger.info(f"Removing item {event.item_id} from search index...")
    try:
        search_service = SearchService()
        search_service.delete_item(event.item_id)
    except Exception as e:
        logger.error(
            f"Failed to remove item {event.item_id} from search: {e}", exc_info=True
        )


def register_search_listeners():
    event_bus.subscribe(ItemCreatedEvent, sync_item_to_search)
    event_bus.subscribe(ItemUpdatedEvent, sync_item_to_search)
    event_bus.subscribe(ItemStateChangedEvent, sync_item_to_search)
    event_bus.subscribe(ItemDeletedEvent, remove_item_from_search)
    logger.info("Search event listeners registered.")
