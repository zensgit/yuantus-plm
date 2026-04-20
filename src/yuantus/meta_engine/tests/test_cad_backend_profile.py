from __future__ import annotations

from types import SimpleNamespace

import pytest

from yuantus.config.cad_backend_profile import (
    cad_connector_base_url_configured,
    cad_connector_enabled_for_profile,
    configured_cad_backend_profile_name,
    effective_cad_backend_profile,
    effective_cad_backend_profile_name,
)
from yuantus.meta_engine.services.job_errors import JobFatalError
from yuantus.meta_engine.tasks import cad_pipeline_tasks


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


def test_auto_profile_without_connector_defaults_to_local_baseline() -> None:
    settings = _settings()

    assert configured_cad_backend_profile_name(settings) == "auto"
    assert effective_cad_backend_profile(settings) == "local"
    assert effective_cad_backend_profile_name(settings) == "local-baseline"
    assert cad_connector_enabled_for_profile(settings) is False


def test_auto_profile_with_optional_connector_defaults_to_hybrid_auto() -> None:
    settings = _settings(base_url="http://cad-connector.local", mode="optional")

    assert configured_cad_backend_profile_name(settings) == "auto"
    assert effective_cad_backend_profile(settings) == "hybrid"
    assert effective_cad_backend_profile_name(settings) == "hybrid-auto"
    assert cad_connector_enabled_for_profile(settings) is True


def test_auto_profile_with_required_connector_defaults_to_external_enterprise() -> None:
    settings = _settings(base_url="http://cad-connector.local", mode="required")

    assert configured_cad_backend_profile_name(settings) == "auto"
    assert effective_cad_backend_profile(settings) == "external"
    assert effective_cad_backend_profile_name(settings) == "external-enterprise"
    assert cad_connector_enabled_for_profile(settings) is True


def test_explicit_local_profile_overrides_legacy_required_mode() -> None:
    settings = _settings(
        profile="local-baseline",
        base_url="http://cad-connector.local",
        mode="required",
    )

    assert configured_cad_backend_profile_name(settings) == "local-baseline"
    assert effective_cad_backend_profile(settings) == "local"
    assert cad_connector_enabled_for_profile(settings) is False


def test_explicit_hybrid_profile_overrides_legacy_disabled_mode() -> None:
    settings = _settings(
        profile="hybrid-auto",
        base_url="http://cad-connector.local",
        mode="disabled",
    )

    assert configured_cad_backend_profile_name(settings) == "hybrid-auto"
    assert effective_cad_backend_profile(settings) == "hybrid"
    assert cad_connector_enabled_for_profile(settings) is True


def test_connector_base_url_configured_is_scope_neutral() -> None:
    settings = _settings(
        profile="local-baseline",
        base_url="http://cad-connector.local",
        mode="disabled",
    )

    assert cad_connector_base_url_configured(settings) is True
    assert cad_connector_enabled_for_profile(settings) is False


def test_scoped_effective_profile_can_enable_connector_even_if_env_profile_is_local(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_settings",
        lambda: _settings(
            profile="local-baseline",
            base_url="http://cad-connector.local",
            mode="disabled",
        ),
    )
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "_cad_backend_profile_resolution",
        lambda session=None: {
            "configured": "hybrid-auto",
            "effective": "hybrid-auto",
            "source": "plugin-config:tenant-org",
            "scope": {"tenant_id": "tenant-1", "org_id": "org-1", "level": "tenant-org"},
        },
    )

    assert cad_pipeline_tasks._cad_connector_enabled() is True


def test_explicit_external_profile_requires_configured_connector(monkeypatch) -> None:
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_settings",
        lambda: _settings(profile="external-enterprise", base_url="", mode="optional"),
    )
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_request_context",
        lambda: SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    )

    with pytest.raises(
        JobFatalError,
        match="external-enterprise",
    ):
        cad_pipeline_tasks._require_connector_for_remote_3d(
            SimpleNamespace(document_type="3d"),
            operation="preview",
        )


def test_profile_resolution_requires_tenant_context(monkeypatch) -> None:
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_request_context",
        lambda: SimpleNamespace(tenant_id=None, org_id="org-1"),
    )

    with pytest.raises(JobFatalError, match="requires tenant context"):
        cad_pipeline_tasks._cad_backend_profile_resolution()
