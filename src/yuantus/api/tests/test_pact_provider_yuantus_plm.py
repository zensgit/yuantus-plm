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
DEFAULT_HOST = os.getenv("YUANTUS_PACT_HOST", "localhost")


def _pact_dir() -> Path:
    return Path(os.getenv("YUANTUS_PACT_DIR", str(DEFAULT_PACT_DIR))).resolve()


def _available_pact_files(pact_dir: Path) -> list[Path]:
    return sorted(path for path in pact_dir.glob("*.json") if path.is_file())


def _find_free_port(host: str = DEFAULT_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
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


def _wait_for_ready(
    health_url: str,
    thread: threading.Thread,
    thread_exception: dict[str, BaseException],
    deadline: float,
) -> None:
    """
    Poll the provider's /api/v1/health until it responds 200, the thread
    dies, or the deadline expires.

    Only readiness-probe exceptions (requests / network) are caught here.
    Anything else propagates.
    """
    last_error: Exception | None = None
    while time.time() < deadline:
        if not thread.is_alive():
            cause = thread_exception.get("error")
            if cause is not None:
                raise RuntimeError(
                    f"Pact provider server crashed during startup: "
                    f"{type(cause).__name__}: {cause}"
                ) from cause
            raise RuntimeError(
                "Pact provider server thread exited cleanly before becoming "
                "ready (uvicorn returned without binding); inspect lifespan "
                "startup hooks in yuantus.api.app._lifespan."
            )
        try:
            response = requests.get(health_url, timeout=0.5)
            if response.ok:
                return
            last_error = RuntimeError(
                f"health endpoint returned {response.status_code}"
            )
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(0.1)

    raise RuntimeError(
        f"Pact provider server did not become ready at {health_url}"
    ) from last_error


@contextlib.contextmanager
def _running_provider(base_host: str = DEFAULT_HOST):
    port = _find_free_port(base_host)
    app = create_app()
    config = uvicorn.Config(app, host=base_host, port=port, log_level="error")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # type: ignore[assignment]

    # Wrap server.run() so any exception inside the thread is captured and
    # surfaced through the readiness loop, instead of disappearing into the
    # generic "thread is not alive" message.
    thread_exception: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            server.run()
        except BaseException as exc:  # noqa: BLE001 - we re-raise via dict
            thread_exception["error"] = exc
            raise

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()

    base_url = f"http://{base_host}:{port}"
    health_url = f"{base_url}/api/v1/health"
    deadline = time.time() + 15.0

    try:
        # Phase 1: wait until the server is ready. Only readiness errors are
        # caught here; the test body's exceptions are NOT swallowed.
        _wait_for_ready(health_url, thread, thread_exception, deadline)

        # Phase 2: hand the live base_url to the test. Any exception raised by
        # the test body propagates normally — the finally below still runs.
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=10.0)


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

    # Add each pact file individually rather than the whole directory.
    # `.add_source(directory)` would attempt to parse every file in the
    # directory (including README.md) and report a Pact JSON parse error.
    verifier = pact.Verifier(DEFAULT_PROVIDER_NAME)
    for path in pact_files:
        verifier = verifier.add_source(str(path))
    verifier = verifier.state_handler(_provider_state_handler, teardown=True)

    with _running_provider() as base_url:
        verifier = verifier.add_transport(url=base_url)
        verifier.verify()
