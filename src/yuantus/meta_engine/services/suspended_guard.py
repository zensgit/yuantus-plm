from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.meta_engine.lifecycle.guard import get_lifecycle_state
from yuantus.meta_engine.lifecycle.models import LifecycleState
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.plugin_config_service import PluginConfigService
from yuantus.meta_engine.version.models import ItemVersion


SUSPENDED_GUARD_PLUGIN_ID = "suspended-guard"
SUSPENDED_GUARD_DISABLED_KEY = "disabled"


_REASON_MESSAGES = {
    "target_suspended": "target item/version is in a suspended state",
    "current_version_suspended": "target item's current version resides on a suspended state",
}


class SuspendedStateError(ValueError):
    def __init__(self, *, reason: str, target_id: str):
        self.reason = reason
        self.target_id = target_id
        message = _REASON_MESSAGES.get(reason, reason)
        super().__init__(message)

    def to_detail(self) -> dict:
        return {
            "error": "SUSPENDED_STATE",
            "reason": self.reason,
            "target_id": self.target_id,
            "message": str(self),
        }


@dataclass(frozen=True)
class GuardScope:
    tenant_id: Optional[str]
    org_id: Optional[str]


class SuspendedGuardService:
    def __init__(self, session: Session, settings: Optional[Any] = None):
        self.session = session
        self.settings = settings or get_settings()

    def is_enabled(self) -> bool:
        if bool(getattr(self.settings, "SUSPENDED_GUARD_DISABLED", False)):
            return False

        scope = self._scope()
        if not scope.tenant_id:
            return True

        config = self._resolve_scoped_config(scope)
        if not isinstance(config, dict):
            return True
        return not bool(config.get(SUSPENDED_GUARD_DISABLED_KEY, False))

    def assert_not_suspended(self, target_id: str, *, context: str) -> None:
        if not self.is_enabled():
            return

        if context == "effectivity":
            self._assert_effectivity_target(target_id)
            return

        item = self.session.get(Item, target_id)
        if not item:
            raise ValueError(f"Item {target_id} not found")
        self._assert_item(item, reason="target_suspended")

    def _scope(self) -> GuardScope:
        ctx = get_request_context()
        return GuardScope(tenant_id=ctx.tenant_id, org_id=ctx.org_id)

    def _resolve_scoped_config(self, scope: GuardScope) -> Optional[dict]:
        plugin_service = PluginConfigService(self.session)

        if scope.org_id:
            org_record = plugin_service.get_config(
                plugin_id=SUSPENDED_GUARD_PLUGIN_ID,
                tenant_id=scope.tenant_id,
                org_id=scope.org_id,
            )
            org_config = getattr(org_record, "config", None)
            if isinstance(org_config, dict):
                return org_config

        tenant_record = plugin_service.get_config(
            plugin_id=SUSPENDED_GUARD_PLUGIN_ID,
            tenant_id=scope.tenant_id,
            org_id=None,
        )
        tenant_config = getattr(tenant_record, "config", None)
        if isinstance(tenant_config, dict):
            return tenant_config
        return None

    def _assert_effectivity_target(self, target_id: str) -> None:
        item = self.session.get(Item, target_id)
        if item:
            if item.related_id:
                related_item = self.session.get(Item, item.related_id)
                if not related_item:
                    raise ValueError(f"Relationship target {item.related_id} not found")
                self._assert_item(related_item, reason="target_suspended")
                return
            self._assert_item(item, reason="target_suspended")
            return

        version = self.session.get(ItemVersion, target_id)
        if not version:
            raise ValueError(f"Effectivity target {target_id} not found")
        self._assert_version(version)

    def _assert_item(self, item: Item, *, reason: str) -> None:
        item_type = self._item_type(item)
        state = get_lifecycle_state(self.session, item, item_type)
        if state and bool(getattr(state, "is_suspended", False)):
            raise SuspendedStateError(reason=reason, target_id=item.id)

    def _assert_version(self, version: ItemVersion) -> None:
        item = self.session.get(Item, version.item_id)
        if item:
            self._assert_item(item, reason="current_version_suspended")
            item_type = self._item_type(item)
            version_state = self._version_lifecycle_state(version, item_type)
            if version_state and bool(getattr(version_state, "is_suspended", False)):
                raise SuspendedStateError(
                    reason="current_version_suspended", target_id=version.id
                )
            return

        raise ValueError(f"Version parent item {version.item_id} not found")

    def _item_type(self, item: Item) -> Optional[ItemType]:
        item_type_id = getattr(item, "item_type_id", None)
        if not item_type_id:
            return None
        return self.session.get(ItemType, item_type_id)

    def _version_lifecycle_state(
        self, version: ItemVersion, item_type: Optional[ItemType]
    ) -> Optional[LifecycleState]:
        version_state = getattr(version, "state", None)
        if not (version_state and item_type and item_type.lifecycle_map_id):
            return None
        return (
            self.session.query(LifecycleState)
            .filter(
                LifecycleState.lifecycle_map_id == item_type.lifecycle_map_id,
                LifecycleState.name == version_state,
            )
            .first()
        )


def assert_not_suspended(session: Session, target_id: str, *, context: str) -> None:
    SuspendedGuardService(session).assert_not_suspended(target_id, context=context)
