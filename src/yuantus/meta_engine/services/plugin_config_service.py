"""
Plugin Config Service
Manages per-tenant/org plugin configuration payloads.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from yuantus.meta_engine.models.plugin_config import PluginConfig


class PluginConfigService:
    def __init__(self, session: Session):
        self.session = session

    def _normalize_scope(
        self, tenant_id: Optional[str], org_id: Optional[str]
    ) -> Tuple[str, str]:
        def _clean(value: Optional[str]) -> str:
            if value is None:
                return "default"
            cleaned = str(value).strip()
            return cleaned or "default"

        return _clean(tenant_id), _clean(org_id)

    def get_config(
        self,
        *,
        plugin_id: str,
        tenant_id: Optional[str],
        org_id: Optional[str],
    ) -> Optional[PluginConfig]:
        tenant_value, org_value = self._normalize_scope(tenant_id, org_id)
        return (
            self.session.query(PluginConfig)
            .filter(
                PluginConfig.plugin_id == plugin_id,
                PluginConfig.tenant_id == tenant_value,
                PluginConfig.org_id == org_value,
            )
            .first()
        )

    def upsert_config(
        self,
        *,
        plugin_id: str,
        config: Dict[str, Any],
        tenant_id: Optional[str],
        org_id: Optional[str],
        user_id: Optional[int] = None,
        merge: bool = False,
    ) -> PluginConfig:
        tenant_value, org_value = self._normalize_scope(tenant_id, org_id)
        existing = (
            self.session.query(PluginConfig)
            .filter(
                PluginConfig.plugin_id == plugin_id,
                PluginConfig.tenant_id == tenant_value,
                PluginConfig.org_id == org_value,
            )
            .first()
        )

        if existing:
            if merge:
                merged = dict(existing.config or {})
                merged.update(config)
                existing.config = merged
            else:
                existing.config = config
            existing.updated_by_id = user_id
            self.session.add(existing)
            self.session.commit()
            return existing

        record = PluginConfig(
            plugin_id=plugin_id,
            tenant_id=tenant_value,
            org_id=org_value,
            config=config,
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        self.session.add(record)
        self.session.commit()
        return record
