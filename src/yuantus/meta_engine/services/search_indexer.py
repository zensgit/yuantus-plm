from __future__ import annotations

import logging
from threading import Lock
from typing import Callable

from yuantus.database import get_db_session
from yuantus.meta_engine.events.domain_events import (
    EcoCreatedEvent,
    EcoDeletedEvent,
    EcoUpdatedEvent,
    ItemCreatedEvent,
    ItemDeletedEvent,
    ItemStateChangedEvent,
    ItemUpdatedEvent,
)
from yuantus.meta_engine.events.event_bus import event_bus
from yuantus.meta_engine.models.eco import ECO
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.search_service import SearchService

logger = logging.getLogger(__name__)

_INDEX_READY = False
_INDEX_LOCK = Lock()
_ECO_INDEX_READY = False
_ECO_INDEX_LOCK = Lock()
_REGISTERED = False
_REGISTER_LOCK = Lock()


def _ensure_index(service: SearchService) -> None:
    global _INDEX_READY
    if _INDEX_READY or not service.client:
        return
    with _INDEX_LOCK:
        if _INDEX_READY:
            return
        try:
            service.ensure_index()
            _INDEX_READY = True
        except Exception:
            logger.exception("Search index initialization failed")


def _ensure_eco_index(service: SearchService) -> None:
    global _ECO_INDEX_READY
    if _ECO_INDEX_READY or not service.client:
        return
    with _ECO_INDEX_LOCK:
        if _ECO_INDEX_READY:
            return
        try:
            service.ensure_eco_index()
            _ECO_INDEX_READY = True
        except Exception:
            logger.exception("ECO search index initialization failed")


def _with_search_service(handler: Callable[[SearchService], None]) -> None:
    try:
        with get_db_session() as session:
            service = SearchService(session)
            if not service.client:
                return
            _ensure_index(service)
            handler(service)
    except Exception:
        logger.exception("Search indexing handler failed")


def _handle_item_created(event: ItemCreatedEvent) -> None:
    def _index(service: SearchService) -> None:
        item = service.session.get(Item, event.item_id) if service.session else None
        if not item:
            logger.debug("Search index skip (item missing): %s", event.item_id)
            return
        service.index_item(item)

    _with_search_service(_index)


def _handle_item_updated(event: ItemUpdatedEvent) -> None:
    def _index(service: SearchService) -> None:
        item = service.session.get(Item, event.item_id) if service.session else None
        if not item:
            logger.debug("Search index skip (item missing): %s", event.item_id)
            return
        service.index_item(item)

    _with_search_service(_index)


def _handle_item_deleted(event: ItemDeletedEvent) -> None:
    def _delete(service: SearchService) -> None:
        service.delete_item(event.item_id)

    _with_search_service(_delete)


def _handle_item_state_changed(event: ItemStateChangedEvent) -> None:
    def _index(service: SearchService) -> None:
        item = service.session.get(Item, event.item_id) if service.session else None
        if not item:
            logger.debug("Search index skip (item missing): %s", event.item_id)
            return
        service.index_item(item)

    _with_search_service(_index)


def _handle_eco_created(event: EcoCreatedEvent) -> None:
    def _index(service: SearchService) -> None:
        _ensure_eco_index(service)
        eco = service.session.get(ECO, event.eco_id) if service.session else None
        if not eco:
            logger.debug("ECO index skip (eco missing): %s", event.eco_id)
            return
        service.index_eco(eco)

    _with_search_service(_index)


def _handle_eco_updated(event: EcoUpdatedEvent) -> None:
    def _index(service: SearchService) -> None:
        _ensure_eco_index(service)
        eco = service.session.get(ECO, event.eco_id) if service.session else None
        if not eco:
            logger.debug("ECO index skip (eco missing): %s", event.eco_id)
            return
        service.index_eco(eco)

    _with_search_service(_index)


def _handle_eco_deleted(event: EcoDeletedEvent) -> None:
    def _delete(service: SearchService) -> None:
        _ensure_eco_index(service)
        service.delete_eco(event.eco_id)

    _with_search_service(_delete)


def register_search_index_handlers() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    with _REGISTER_LOCK:
        if _REGISTERED:
            return
        event_bus.subscribe(ItemCreatedEvent, _handle_item_created)
        event_bus.subscribe(ItemUpdatedEvent, _handle_item_updated)
        event_bus.subscribe(ItemStateChangedEvent, _handle_item_state_changed)
        event_bus.subscribe(ItemDeletedEvent, _handle_item_deleted)
        event_bus.subscribe(EcoCreatedEvent, _handle_eco_created)
        event_bus.subscribe(EcoUpdatedEvent, _handle_eco_updated)
        event_bus.subscribe(EcoDeletedEvent, _handle_eco_deleted)
        _REGISTERED = True
        logger.info("Search index handlers registered")
