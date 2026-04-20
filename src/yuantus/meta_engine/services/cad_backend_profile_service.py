from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from yuantus.config import (
    available_cad_backend_profiles,
    cad_backend_profile_source,
    configured_cad_backend_profile_name,
    effective_cad_backend_profile_name,
    normalize_cad_backend_profile,
)
from yuantus.meta_engine.services.plugin_config_service import PluginConfigService

CAD_BACKEND_PROFILE_PLUGIN_ID = "cad-backend-profile"
CAD_BACKEND_PROFILE_CONFIG_KEY = "backend_profile"


@dataclass(frozen=True)
class CadBackendProfileResolution:
    configured: str
    effective: str
    source: str
    options: list[str]
    scope: Dict[str, Optional[str]]


class CadBackendProfileService:
    def __init__(self, session: Optional[Session], settings: Any):
        self.session = session
        self.settings = settings

    def _extract_profile(self, payload: Optional[dict]) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        raw = payload.get(CAD_BACKEND_PROFILE_CONFIG_KEY)
        if raw is None:
            raw = payload.get("profile")
        raw_text = str(raw or "").strip().lower()
        if raw_text not in {
            "local",
            "local-baseline",
            "hybrid",
            "hybrid-auto",
            "external",
            "external-enterprise",
        }:
            return None
        normalized = normalize_cad_backend_profile(raw_text)
        if normalized == "local":
            return "local-baseline"
        if normalized == "hybrid":
            return "hybrid-auto"
        return "external-enterprise"

    def _plugin_config_service(self) -> Optional[PluginConfigService]:
        if self.session is None:
            return None
        return PluginConfigService(self.session)

    def _resolve_scoped_override(
        self, *, tenant_id: Optional[str], org_id: Optional[str]
    ) -> Optional[CadBackendProfileResolution]:
        if not tenant_id:
            return None

        plugin_service = self._plugin_config_service()
        if plugin_service is None:
            return None

        if org_id:
            record = plugin_service.get_config(
                plugin_id=CAD_BACKEND_PROFILE_PLUGIN_ID,
                tenant_id=tenant_id,
                org_id=org_id,
            )
            profile = self._extract_profile(getattr(record, "config", None))
            if profile:
                return CadBackendProfileResolution(
                    configured=profile,
                    effective=profile,
                    source="plugin-config:tenant-org",
                    options=available_cad_backend_profiles(),
                    scope={
                        "tenant_id": str(tenant_id),
                        "org_id": str(org_id),
                        "level": "tenant-org",
                    },
                )

        record = plugin_service.get_config(
            plugin_id=CAD_BACKEND_PROFILE_PLUGIN_ID,
            tenant_id=tenant_id,
            org_id=None,
        )
        profile = self._extract_profile(getattr(record, "config", None))
        if profile:
            return CadBackendProfileResolution(
                configured=profile,
                effective=profile,
                source="plugin-config:tenant-default",
                options=available_cad_backend_profiles(),
                scope={
                    "tenant_id": str(tenant_id),
                    "org_id": None,
                    "level": "tenant-default",
                },
            )
        return None

    def resolve(
        self, *, tenant_id: Optional[str], org_id: Optional[str]
    ) -> CadBackendProfileResolution:
        scoped = self._resolve_scoped_override(tenant_id=tenant_id, org_id=org_id)
        if scoped is not None:
            return scoped
        return CadBackendProfileResolution(
            configured=configured_cad_backend_profile_name(self.settings),
            effective=effective_cad_backend_profile_name(self.settings),
            source=cad_backend_profile_source(self.settings),
            options=available_cad_backend_profiles(),
            scope={
                "tenant_id": str(tenant_id) if tenant_id else None,
                "org_id": str(org_id) if org_id else None,
                "level": "environment",
            },
        )

    def update_override(
        self,
        *,
        tenant_id: Optional[str],
        org_id: Optional[str],
        user_id: Optional[int],
        profile: str,
        scope: str,
    ) -> CadBackendProfileResolution:
        if profile not in set(available_cad_backend_profiles()):
            raise ValueError(
                "profile must be one of: " + ", ".join(available_cad_backend_profiles())
            )
        if not tenant_id:
            raise ValueError("tenant_id context required")
        if scope not in {"org", "tenant"}:
            raise ValueError("scope must be org or tenant")
        if scope == "org" and not org_id:
            raise ValueError("org scope requires org_id context")

        plugin_service = self._plugin_config_service()
        if plugin_service is None:
            raise ValueError("session required")

        plugin_service.upsert_config(
            plugin_id=CAD_BACKEND_PROFILE_PLUGIN_ID,
            config={CAD_BACKEND_PROFILE_CONFIG_KEY: profile},
            tenant_id=tenant_id,
            org_id=org_id if scope == "org" else None,
            user_id=user_id,
            merge=True,
        )
        return self.resolve(tenant_id=tenant_id, org_id=org_id)

    def delete_override(
        self,
        *,
        tenant_id: Optional[str],
        org_id: Optional[str],
        scope: str,
    ) -> CadBackendProfileResolution:
        if not tenant_id:
            raise ValueError("tenant_id context required")
        if scope not in {"org", "tenant"}:
            raise ValueError("scope must be org or tenant")
        if scope == "org" and not org_id:
            raise ValueError("org scope requires org_id context")

        plugin_service = self._plugin_config_service()
        if plugin_service is None:
            raise ValueError("session required")

        plugin_service.delete_config(
            plugin_id=CAD_BACKEND_PROFILE_PLUGIN_ID,
            tenant_id=tenant_id,
            org_id=org_id if scope == "org" else None,
        )
        return self.resolve(tenant_id=tenant_id, org_id=org_id)
