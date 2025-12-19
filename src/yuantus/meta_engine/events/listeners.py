"""
Event Listeners for PLM Meta Engine.
These functions subscribe to domain events and react to them.
"""

import logging
from typing import List, Union

from yuantus.meta_engine.events.event_bus import event_bus
from yuantus.meta_engine.events.domain_events import (
    DomainEvent,
    ItemCreatedEvent,
    ItemUpdatedEvent,
    ItemDeletedEvent,
    ItemStateChangedEvent,
    FileUploadedEvent,
    FileCheckedInEvent,
    CadAttributesSyncedEvent,
)

logger = logging.getLogger(__name__)

# A simple in-memory list to track received events for testing/debugging
received_events: List[DomainEvent] = []


def generic_event_logger(event: DomainEvent):
    """Logs all events."""
    logger.info(f"[{event.event_type}] Event received: {event.event_id}")
    received_events.append(event)  # Store for inspection


def item_change_logger(
    event: Union[
        ItemCreatedEvent, ItemUpdatedEvent, ItemDeletedEvent, ItemStateChangedEvent
    ],
):
    """Logs item-specific changes with more detail."""
    logger.info(
        f"Item Event ({event.event_type}): Item {getattr(event, 'item_id', 'N/A')} by Actor {event.actor_id}"
    )
    if isinstance(event, ItemStateChangedEvent):
        logger.info(f"  State changed: {event.old_state} -> {event.new_state}")
    elif isinstance(event, ItemUpdatedEvent):
        logger.info(f"  Changes: {event.changes}")


def file_upload_listener(event: FileUploadedEvent):
    """Example listener for file uploads."""
    logger.info(
        f"File Uploaded: {event.file_name} (Size: {event.file_size}) to {event.storage_key}"
    )


def file_checked_in_listener(event: FileCheckedInEvent):
    """Example listener for file check-in."""
    logger.info(
        f"File Checked-In: Item {event.item_id}, File {event.file_id}, New Version {event.new_version_id}"
    )


def cad_sync_listener(event: CadAttributesSyncedEvent):
    """Example listener for CAD attribute sync."""
    logger.info(
        f"CAD Attributes Synced: Item {event.item_id}, File {event.file_id}, Attributes: {event.synced_attributes}"
    )


# Function to initialize all listeners
def initialize_listeners():
    event_bus.subscribe(DomainEvent, generic_event_logger)  # Subscribe to all events
    event_bus.subscribe(ItemCreatedEvent, item_change_logger)
    event_bus.subscribe(ItemUpdatedEvent, item_change_logger)
    event_bus.subscribe(ItemDeletedEvent, item_change_logger)
    event_bus.subscribe(ItemStateChangedEvent, item_change_logger)
    event_bus.subscribe(FileUploadedEvent, file_upload_listener)
    event_bus.subscribe(FileCheckedInEvent, file_checked_in_listener)
    event_bus.subscribe(CadAttributesSyncedEvent, cad_sync_listener)

    logger.info("All domain event listeners initialized.")
