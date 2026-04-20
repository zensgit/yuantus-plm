from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.services.cad_backend_profile_service import (
    CadBackendProfileService,
)


def _settings(
    *,
    profile: str = "auto",
    base_url: str = "",
    mode: str = "optional",
) -> SimpleNamespace:
    return SimpleNamespace(
        CAD_CONVERSION_BACKEND_PROFILE=profile,
        CAD_CONNECTOR_BASE_URL=base_url,
        CAD_CONNECTOR_MODE=mode,
    )


def _record(profile: str) -> SimpleNamespace:
    return SimpleNamespace(config={"backend_profile": profile})


def test_resolve_uses_org_override_before_environment() -> None:
    plugin_service = MagicMock()
    plugin_service.get_config.return_value = _record("local-baseline")

    with patch(
        "yuantus.meta_engine.services.cad_backend_profile_service.PluginConfigService",
        return_value=plugin_service,
    ):
        resolution = CadBackendProfileService(
            MagicMock(),
            _settings(profile="external-enterprise"),
        ).resolve(tenant_id="tenant-1", org_id="org-1")

    assert resolution.configured == "local-baseline"
    assert resolution.effective == "local-baseline"
    assert resolution.source == "plugin-config:tenant-org"
    assert resolution.scope == {
        "tenant_id": "tenant-1",
        "org_id": "org-1",
        "level": "tenant-org",
    }


def test_resolve_falls_back_to_tenant_default_override() -> None:
    plugin_service = MagicMock()
    plugin_service.get_config.side_effect = [None, _record("hybrid-auto")]

    with patch(
        "yuantus.meta_engine.services.cad_backend_profile_service.PluginConfigService",
        return_value=plugin_service,
    ):
        resolution = CadBackendProfileService(
            MagicMock(),
            _settings(profile="external-enterprise"),
        ).resolve(tenant_id="tenant-1", org_id="org-1")

    assert resolution.configured == "hybrid-auto"
    assert resolution.effective == "hybrid-auto"
    assert resolution.source == "plugin-config:tenant-default"
    assert resolution.scope == {
        "tenant_id": "tenant-1",
        "org_id": None,
        "level": "tenant-default",
    }


def test_resolve_ignores_invalid_override_and_falls_back_to_environment() -> None:
    plugin_service = MagicMock()
    plugin_service.get_config.side_effect = [_record("bogus-profile"), None]

    with patch(
        "yuantus.meta_engine.services.cad_backend_profile_service.PluginConfigService",
        return_value=plugin_service,
    ):
        resolution = CadBackendProfileService(
            MagicMock(),
            _settings(profile="auto", base_url="http://cad-connector.local", mode="required"),
        ).resolve(tenant_id="tenant-1", org_id="org-1")

    assert resolution.configured == "auto"
    assert resolution.effective == "external-enterprise"
    assert resolution.source == "legacy-mode"
    assert resolution.scope == {
        "tenant_id": "tenant-1",
        "org_id": "org-1",
        "level": "environment",
    }
