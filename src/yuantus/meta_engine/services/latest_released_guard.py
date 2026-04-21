from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.plugin_config_service import PluginConfigService
from yuantus.meta_engine.version.models import ItemVersion


LATEST_RELEASED_GUARD_PLUGIN_ID = "latest-released-guard"
LATEST_RELEASED_GUARD_DISABLED_KEY = "disabled"


_REASON_MESSAGES = {
    "not_latest_released": "target is not the latest current item/version",
    "current_version_missing": "current item version is missing",
    "current_version_not_released": "current version is not released",
}


class NotLatestReleasedError(ValueError):
    def __init__(self, *, reason: str, target_id: str):
        self.reason = reason
        self.target_id = target_id
        message = _REASON_MESSAGES.get(reason, reason)
        super().__init__(message)

    def to_detail(self) -> dict:
        return {
            "error": "NOT_LATEST_RELEASED",
            "reason": self.reason,
            "target_id": self.target_id,
            "message": str(self),
        }


@dataclass(frozen=True)
class GuardScope:
    tenant_id: Optional[str]
    org_id: Optional[str]


class LatestReleasedGuardService:
    def __init__(self, session: Session, settings: Optional[Any] = None):
        self.session = session
        self.settings = settings or get_settings()

    def is_enabled(self) -> bool:
        if bool(getattr(self.settings, "LATEST_RELEASED_GUARD_DISABLED", False)):
            return False

        scope = self._scope()
        if not scope.tenant_id:
            return True

        config = self._resolve_scoped_config(scope)
        if not isinstance(config, dict):
            return True
        return not bool(config.get(LATEST_RELEASED_GUARD_DISABLED_KEY, False))

    def assert_latest_released(self, target_id: str, *, context: str) -> None:
        if not self.is_enabled():
            return

        if context == "effectivity":
            self._assert_effectivity_target(target_id)
            return

        item = self.session.get(Item, target_id)
        if not item:
            raise ValueError(f"Item {target_id} not found")
        self._assert_item(item)

    def _scope(self) -> GuardScope:
        ctx = get_request_context()
        return GuardScope(tenant_id=ctx.tenant_id, org_id=ctx.org_id)

    def _resolve_scoped_config(self, scope: GuardScope) -> Optional[dict]:
        plugin_service = PluginConfigService(self.session)

        if scope.org_id:
            org_record = plugin_service.get_config(
                plugin_id=LATEST_RELEASED_GUARD_PLUGIN_ID,
                tenant_id=scope.tenant_id,
                org_id=scope.org_id,
            )
            org_config = getattr(org_record, "config", None)
            if isinstance(org_config, dict):
                return org_config

        tenant_record = plugin_service.get_config(
            plugin_id=LATEST_RELEASED_GUARD_PLUGIN_ID,
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
                if not bool(item.is_current):
                    raise NotLatestReleasedError(
                        reason="not_latest_released",
                        target_id=item.id,
                    )
                related_item = self.session.get(Item, item.related_id)
                if not related_item:
                    raise ValueError(f"Relationship target {item.related_id} not found")
                self._assert_item(related_item)
                return
            self._assert_item(item)
            return

        version = self.session.get(ItemVersion, target_id)
        if not version:
            raise ValueError(f"Effectivity target {target_id} not found")
        self._assert_version(version)

    def _assert_item(self, item: Item) -> None:
        if not bool(item.is_current):
            raise NotLatestReleasedError(reason="not_latest_released", target_id=item.id)

        if not item.current_version_id:
            raise NotLatestReleasedError(reason="current_version_missing", target_id=item.id)

        version = self.session.get(ItemVersion, item.current_version_id)
        if not version:
            raise NotLatestReleasedError(reason="current_version_missing", target_id=item.id)
        self._assert_version(version)

    def _assert_version(self, version: ItemVersion) -> None:
        if not bool(version.is_current):
            raise NotLatestReleasedError(reason="not_latest_released", target_id=version.id)
        if not bool(version.is_released):
            raise NotLatestReleasedError(
                reason="current_version_not_released", target_id=version.id
            )

        item = self.session.get(Item, version.item_id)
        if item and (not bool(item.is_current) or item.current_version_id != version.id):
            raise NotLatestReleasedError(reason="not_latest_released", target_id=version.id)


def assert_latest_released(session: Session, target_id: str, *, context: str) -> None:
    LatestReleasedGuardService(session).assert_latest_released(target_id, context=context)
