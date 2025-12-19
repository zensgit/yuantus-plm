"""
In-memory Event Bus for Domain Events.
Provides a simple publish/subscribe mechanism.
"""

import logging  # Added logging
from typing import Callable, List, Dict, Type
from threading import Lock

from yuantus.meta_engine.events.domain_events import DomainEvent

logger = logging.getLogger(__name__)  # Initialize logger

EventHandler = Callable[[DomainEvent], None]


class EventBus:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subscribers: Dict[
                    Type[DomainEvent], List[EventHandler]
                ] = {}
            return cls._instance

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler):
        """
        Subscribes a handler function to a specific event type.
        Args:
            event_type: The type of the DomainEvent to subscribe to.
            handler: A callable that takes a DomainEvent instance as its argument.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler {handler.__name__} to {event_type.__name__}")

    def publish(self, event: DomainEvent):
        """
        Publishes an event to all subscribed handlers.
        Args:
            event: The DomainEvent instance to publish.
        """
        logger.debug(f"Publishing event: {event.event_type} (ID: {event.event_id})")

        # Publish to handlers specific to the event's exact type
        handlers_for_exact_type = self._subscribers.get(type(event), [])
        for handler in handlers_for_exact_type:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Event handler {handler.__name__} for {type(event).__name__} failed: {e}",
                    exc_info=True,
                )

        # Also publish to handlers subscribed to base DomainEvent (if any)
        # This allows generic listeners.
        handlers_for_base_type = self._subscribers.get(DomainEvent, [])
        for handler in handlers_for_base_type:
            if (
                type(event) is not DomainEvent
                and handler not in handlers_for_exact_type
            ):  # Avoid double-processing
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        f"Generic event handler {handler.__name__} for base DomainEvent failed: {e}",
                        exc_info=True,
                    )


# Global instance of the EventBus
event_bus = EventBus()
