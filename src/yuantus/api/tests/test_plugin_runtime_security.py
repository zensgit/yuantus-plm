from __future__ import annotations

from types import SimpleNamespace

from fastapi import APIRouter, FastAPI

from yuantus.config.settings import Settings
from yuantus.plugin_manager import runtime as plugin_runtime
from yuantus.plugin_manager import worker as plugin_worker


class _DummyPlugin:
    def __init__(self, plugin_id: str, *, instance=None, module=None) -> None:
        self.id = plugin_id
        self._instance = instance
        self._module = module

    def get_instance(self):
        return self._instance

    def get_module(self):
        return self._module


class _DummyManager:
    def __init__(self, plugins: list[_DummyPlugin]) -> None:
        self._plugins = plugins
        self.discovered = False
        self.loaded: list[str] = []
        self.activated: list[str] = []

    def discover_plugins(self) -> list[_DummyPlugin]:
        self.discovered = True
        return list(self._plugins)

    def list_plugins(self) -> list[_DummyPlugin]:
        return list(self._plugins)

    def load_plugin(self, plugin_id: str) -> bool:
        self.loaded.append(plugin_id)
        return True

    def activate_plugin(self, plugin_id: str) -> bool:
        self.activated.append(plugin_id)
        return True


def _settings(*, autoload: bool, enabled: str) -> SimpleNamespace:
    return SimpleNamespace(
        PLUGIN_DIRS="./plugins",
        PLUGINS_AUTOLOAD=autoload,
        PLUGINS_ENABLED=enabled,
    )


def test_settings_defaults_are_fail_closed(monkeypatch) -> None:
    for key in (
        "YUANTUS_AUTH_MODE",
        "YUANTUS_PLUGINS_AUTOLOAD",
        "YUANTUS_PLUGINS_ENABLED",
        "YUANTUS_PLUGIN_DIRS",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)

    assert settings.AUTH_MODE == "required"
    assert settings.PLUGINS_AUTOLOAD is False


def test_runtime_skips_plugin_manager_when_plugins_not_explicitly_enabled(monkeypatch) -> None:
    app = FastAPI()

    monkeypatch.setattr(plugin_runtime, "get_settings", lambda: _settings(autoload=False, enabled=""))

    class _ExplodingManager:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("PluginManager should not be instantiated when plugins are disabled")

    monkeypatch.setattr(plugin_runtime, "PluginManager", _ExplodingManager)

    assert plugin_runtime.load_plugins(app) is None
    assert not hasattr(app.state, "plugin_manager")


def test_runtime_loads_only_allowlisted_plugins_when_autoload_is_disabled(monkeypatch) -> None:
    app = FastAPI()
    router = APIRouter(prefix="/allowlisted")

    @router.get("/ping")
    def _ping() -> dict[str, bool]:
        return {"ok": True}

    allowed = _DummyPlugin("allowed", instance=SimpleNamespace(router=router))
    blocked = _DummyPlugin("blocked", instance=SimpleNamespace(router=APIRouter(prefix="/blocked")))
    manager = _DummyManager([allowed, blocked])

    monkeypatch.setattr(plugin_runtime, "get_settings", lambda: _settings(autoload=False, enabled="allowed"))
    monkeypatch.setattr(plugin_runtime, "PluginManager", lambda _dirs: manager)

    loaded = plugin_runtime.load_plugins(app)

    assert loaded is manager
    assert manager.discovered is True
    assert manager.loaded == ["allowed"]
    assert manager.activated == ["allowed"]
    assert hasattr(app.state, "plugin_manager")
    assert any(route.path == "/api/v1/allowlisted/ping" for route in app.router.routes)


def test_worker_skips_plugin_registration_when_plugins_not_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setattr(plugin_worker, "get_settings", lambda: _settings(autoload=False, enabled=""))

    class _ExplodingManager:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("PluginManager should not be instantiated when plugins are disabled")

    monkeypatch.setattr(plugin_worker, "PluginManager", _ExplodingManager)

    assert plugin_worker.register_plugin_job_handlers(object()) == 0


def test_worker_registers_only_allowlisted_plugin_handlers(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Target:
        def __init__(self, name: str) -> None:
            self._name = name

        def register_job_handlers(self, worker_obj) -> None:
            calls.append((self._name, worker_obj))

    allowed = _DummyPlugin("allowed", instance=_Target("allowed"))
    blocked = _DummyPlugin("blocked", instance=_Target("blocked"))
    manager = _DummyManager([allowed, blocked])
    worker_obj = object()

    monkeypatch.setattr(plugin_worker, "get_settings", lambda: _settings(autoload=False, enabled="allowed"))
    monkeypatch.setattr(plugin_worker, "PluginManager", lambda _dirs: manager)

    registered = plugin_worker.register_plugin_job_handlers(worker_obj)

    assert registered == 1
    assert manager.discovered is True
    assert manager.loaded == ["allowed"]
    assert manager.activated == ["allowed"]
    assert calls == [("allowed", worker_obj)]
