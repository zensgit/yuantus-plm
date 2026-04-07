from __future__ import annotations

import contextlib
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
import requests
import uvicorn

from yuantus.api.app import create_app

PACT_DOCS_URL = "https://docs.pact.io/implementation_guides/python/docs/provider"
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PACT_DIR = REPO_ROOT / "contracts" / "pacts"
DEFAULT_PROVIDER_NAME = os.getenv("YUANTUS_PACT_PROVIDER_NAME", "YuantusPLM")
DEFAULT_HOST = os.getenv("YUANTUS_PACT_HOST", "127.0.0.1")


def _pact_dir() -> Path:
    return Path(os.getenv("YUANTUS_PACT_DIR", str(DEFAULT_PACT_DIR))).resolve()


def _available_pact_files(pact_dir: Path) -> list[Path]:
    return sorted(path for path in pact_dir.glob("*.json") if path.is_file())


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((DEFAULT_HOST, 0))
        return int(sock.getsockname()[1])


def _provider_state_handler(
    state: str,
    action: str,
    parameters: dict[str, Any] | None,
) -> None:
    """
    Minimal state handler scaffold for Pact provider verification.

    Extend this mapping when Metasheet consumer tests begin declaring provider
    states. For now we accept no-op setup/teardown so the verifier skeleton can
    land before the first pact artifact is committed.
    """

    _ = (state, action, parameters)
    return None


@contextlib.contextmanager
def _running_provider(base_host: str = DEFAULT_HOST):
    port = _find_free_port()
    app = create_app()
    config = uvicorn.Config(app, host=base_host, port=port, log_level="error")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # type: ignore[assignment]
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://{base_host}:{port}"
    health_url = f"{base_url}/api/v1/health"
    deadline = time.time() + 15.0
    last_error: Exception | None = None

    while time.time() < deadline:
        if not thread.is_alive():
            raise RuntimeError("Pact provider server exited before becoming ready")
        try:
            response = requests.get(health_url, timeout=0.5)
            if response.ok:
                try:
                    yield base_url
                finally:
                    server.should_exit = True
                    thread.join(timeout=10.0)
                return
        except Exception as exc:  # pragma: no cover - readiness polling
            last_error = exc
        time.sleep(0.1)

    server.should_exit = True
    thread.join(timeout=10.0)
    raise RuntimeError(
        f"Pact provider server did not become ready at {health_url}"
    ) from last_error


def test_yuantus_provider_verifies_local_pacts():
    """
    Verify Yuantus against committed consumer pact files.

    This test intentionally skips when the Pact runtime or pact artifacts are
    not present yet. That lets the repository land the verification skeleton
    before Metasheet publishes the first contract set.

    Reference:
    https://docs.pact.io/implementation_guides/python/docs/provider
    """

    pact = pytest.importorskip(
        "pact",
        reason="Install pact-python to enable provider verification",
    )
    pact_dir = _pact_dir()
    pact_files = _available_pact_files(pact_dir)
    if not pact_files:
        pytest.skip(
            f"No pact files found in {pact_dir}. Expected consumer artifacts such as "
            "'metasheet2-yuantus-plm.json'."
        )

    verifier = pact.Verifier(DEFAULT_PROVIDER_NAME).add_source(str(pact_dir))
    verifier = verifier.state_handler(_provider_state_handler, teardown=True)

    with _running_provider() as base_url:
        verifier = verifier.add_transport(url=base_url)
        verifier.verify()
