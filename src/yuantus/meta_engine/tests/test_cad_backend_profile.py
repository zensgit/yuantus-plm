from __future__ import annotations

from types import SimpleNamespace

import pytest

from yuantus.config.cad_backend_profile import (
    cad_connector_base_url_configured,
    cad_connector_enabled_for_profile,
    configured_cad_step_iges_backend_name,
    configured_cad_backend_profile_name,
    effective_cad_backend_profile,
    effective_cad_backend_profile_name,
    effective_cad_step_iges_backend,
)
from yuantus.meta_engine.services.job_errors import JobFatalError
from yuantus.meta_engine.tasks import cad_pipeline_tasks


def _settings(
    *,
    profile: str = "auto",
    base_url: str = "",
    mode: str = "optional",
    step_iges_backend: str = "auto",
) -> SimpleNamespace:
    return SimpleNamespace(
        CAD_CONVERSION_BACKEND_PROFILE=profile,
        CAD_CONNECTOR_BASE_URL=base_url,
        CAD_CONNECTOR_MODE=mode,
        CAD_STEP_IGES_BACKEND=step_iges_backend,
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


def test_step_iges_backend_auto_uses_connector_for_hybrid_with_base_url() -> None:
    settings = _settings(
        profile="hybrid-auto",
        base_url="http://cad-connector.local",
        mode="disabled",
    )

    assert configured_cad_step_iges_backend_name(settings) == "auto"
    assert (
        effective_cad_step_iges_backend(settings, effective_profile="hybrid-auto")
        == "connector"
    )


def test_step_iges_backend_explicit_local_overrides_hybrid_connector() -> None:
    settings = _settings(
        profile="hybrid-auto",
        base_url="http://cad-connector.local",
        mode="disabled",
        step_iges_backend="local",
    )

    assert configured_cad_step_iges_backend_name(settings) == "local"
    assert (
        effective_cad_step_iges_backend(settings, effective_profile="hybrid-auto")
        == "local"
    )


def test_step_iges_backend_keeps_strict_local_profile_local() -> None:
    settings = _settings(
        profile="local-baseline",
        base_url="http://cad-connector.local",
        mode="required",
        step_iges_backend="connector",
    )

    assert (
        effective_cad_step_iges_backend(settings, effective_profile="local-baseline")
        == "local"
    )


def test_step_iges_backend_keeps_external_profile_connector_required() -> None:
    settings = _settings(
        profile="external-enterprise",
        base_url="http://cad-connector.local",
        mode="optional",
        step_iges_backend="local",
    )

    assert (
        effective_cad_step_iges_backend(
            settings,
            effective_profile="external-enterprise",
        )
        == "connector"
    )


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


def test_step_iges_explicit_local_disables_connector_for_step_file(monkeypatch) -> None:
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_settings",
        lambda: _settings(
            profile="hybrid-auto",
            base_url="http://cad-connector.local",
            mode="optional",
            step_iges_backend="local",
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

    file_container = SimpleNamespace(filename="part.step", cad_format="STEP")

    assert cad_pipeline_tasks._cad_connector_enabled_for_file(file_container) is False


def test_step_iges_explicit_connector_enables_connector_for_step_file(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_settings",
        lambda: _settings(
            profile="hybrid-auto",
            base_url="http://cad-connector.local",
            mode="optional",
            step_iges_backend="connector",
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

    file_container = SimpleNamespace(filename="part.step", cad_format="STEP")

    assert cad_pipeline_tasks._cad_connector_enabled_for_file(file_container) is True


def test_step_iges_backend_does_not_affect_non_step_iges_files(monkeypatch) -> None:
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_settings",
        lambda: _settings(
            profile="hybrid-auto",
            base_url="http://cad-connector.local",
            mode="optional",
            step_iges_backend="local",
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

    file_container = SimpleNamespace(filename="native.prt", cad_format="PRT")

    assert cad_pipeline_tasks._cad_connector_enabled_for_file(file_container) is True


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


@pytest.mark.parametrize("tenant_id", [None, "", "   "])
def test_profile_resolution_requires_tenant_context(monkeypatch, tenant_id) -> None:
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_request_context",
        lambda: SimpleNamespace(tenant_id=tenant_id, org_id="org-1"),
    )

    with pytest.raises(JobFatalError, match="requires tenant context"):
        cad_pipeline_tasks._cad_backend_profile_resolution()


def test_profile_resolution_strips_tenant_context_before_resolution(monkeypatch) -> None:
    recorded: dict[str, str | None] = {}

    class _ProfileService:
        def __init__(self, session, settings) -> None:
            pass

        def resolve(self, *, tenant_id: str, org_id: str | None):
            recorded["tenant_id"] = tenant_id
            recorded["org_id"] = org_id
            return SimpleNamespace(
                configured="hybrid-auto",
                effective="hybrid-auto",
                source="plugin-config:tenant-org",
                scope={"tenant_id": tenant_id, "org_id": org_id, "level": "tenant-org"},
            )

    monkeypatch.setattr(
        cad_pipeline_tasks,
        "get_request_context",
        lambda: SimpleNamespace(tenant_id=" tenant-1 ", org_id="org-1"),
    )
    monkeypatch.setattr(
        cad_pipeline_tasks,
        "CadBackendProfileService",
        _ProfileService,
    )

    resolution = cad_pipeline_tasks._cad_backend_profile_resolution()

    assert recorded == {"tenant_id": "tenant-1", "org_id": "org-1"}
    assert resolution["scope"]["tenant_id"] == "tenant-1"
