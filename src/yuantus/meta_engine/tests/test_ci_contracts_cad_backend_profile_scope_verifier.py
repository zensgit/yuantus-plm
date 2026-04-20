from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


class _VerifierFailureHandler(BaseHTTPRequestHandler):
    server: "_VerifierFailureServer"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        state = self.server.state
        parsed = urlparse(self.path)
        if parsed.path == "/api/v1/cad/backend-profile":
            self._write_json(
                200,
                {
                    "configured": state["configured"],
                    "effective": state["effective"],
                    "source": state["source"],
                    "options": ["local-baseline", "hybrid-auto", "external-enterprise"],
                    "scope": {
                        "tenant_id": "tenant-1",
                        "org_id": "org-1",
                        "level": "tenant-org",
                    },
                },
            )
            return
        if parsed.path == "/api/v1/cad/capabilities":
            state["capabilities_calls"] += 1
            self._write_json(500, {"detail": "boom"})
            return
        self._write_json(404, {"detail": "not found"})

    def do_PUT(self) -> None:  # noqa: N802
        state = self.server.state
        parsed = urlparse(self.path)
        if parsed.path != "/api/v1/cad/backend-profile":
            self._write_json(404, {"detail": "not found"})
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length) or b"{}")
        scope = payload.get("scope")
        profile = payload.get("profile")
        source = "plugin-config:tenant-org" if scope == "org" else "plugin-config:tenant-default"
        state["puts"].append(payload)
        state["configured"] = profile
        state["effective"] = profile
        state["source"] = source
        if state["fail_put_after_apply"]:
            state["fail_put_after_apply"] = False
            self._write_json(500, {"detail": "apply_then_fail"})
            return
        self._write_json(
            200,
            {
                "configured": profile,
                "effective": profile,
                "source": source,
                "options": ["local-baseline", "hybrid-auto", "external-enterprise"],
                "scope": {
                    "tenant_id": "tenant-1",
                    "org_id": "org-1",
                    "level": "tenant-org" if scope == "org" else "tenant-default",
                },
            },
        )

    def do_DELETE(self) -> None:  # noqa: N802
        state = self.server.state
        parsed = urlparse(self.path)
        if parsed.path != "/api/v1/cad/backend-profile":
            self._write_json(404, {"detail": "not found"})
            return
        scope = parse_qs(parsed.query).get("scope", [""])[0]
        state["deletes"].append(scope)
        state["configured"] = state["initial"]["configured"]
        state["effective"] = state["initial"]["effective"]
        state["source"] = state["initial"]["source"]
        self._write_json(200, {"ok": True})


class _VerifierFailureServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class):
        super().__init__(server_address, handler_class)
        self.state = {
            "initial": {
                "configured": "",
                "effective": "local-baseline",
                "source": "legacy-mode",
            },
            "configured": "",
            "effective": "local-baseline",
            "source": "legacy-mode",
            "puts": [],
            "deletes": [],
            "capabilities_calls": 0,
            "fail_put_after_apply": False,
        }


def test_cad_backend_profile_scope_verifier_is_documented_and_runnable() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_cad_backend_profile_scope.sh"
    scripts_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"
    connector_doc = repo_root / "docs" / "CAD_CONNECTORS.md"
    dev_doc = repo_root / "docs" / "DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md"
    delivery_doc_index = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"

    for path in (script, scripts_index, connector_doc, dev_doc, delivery_doc_index):
        assert path.is_file(), f"Missing required path: {path}"

    syntax_cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(script)],
        text=True,
        capture_output=True,
    )
    assert syntax_cp.returncode == 0, syntax_cp.stdout + "\n" + syntax_cp.stderr

    help_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_cp.returncode == 0, help_cp.stdout + "\n" + help_cp.stderr
    help_out = help_cp.stdout or ""
    for token in (
        "Usage:",
        "verify_cad_backend_profile_scope.sh",
        "BASE_URL",
        "TOKEN=<jwt>",
        "LOGIN_USERNAME=<user> PASSWORD=<password>",
        "$HOME/.config/yuantus/p2-shared-dev.env",
        "RUN_TENANT_SCOPE",
        "GET  /api/v1/cad/backend-profile",
        "GET  /api/v1/cad/capabilities",
        "DELETE or restore org override",
        "even on failure/interruption",
        "Tenant-default verification is skipped if an org override is active",
    ):
        assert token in help_out, f"help output missing token: {token}"

    scripts_index_text = _read(scripts_index)
    for token in (
        "verify_cad_backend_profile_scope.sh",
        "verifies `GET/PUT/DELETE /api/v1/cad/backend-profile` plus `GET /api/v1/cad/capabilities`",
        "restores the original org scope",
    ):
        assert token in scripts_index_text, f"DELIVERY_SCRIPTS_INDEX missing token: {token}"

    connector_doc_text = _read(connector_doc)
    for token in (
        "/api/v1/cad/backend-profile",
        "verify_cad_backend_profile_scope.sh",
        "safely restores the original org scope",
        "LOGIN_USERNAME=admin PASSWORD=admin",
        "skips tenant-default verification when an active org override masks the tenant-default read surface",
    ):
        assert token in connector_doc_text, f"CAD_CONNECTORS.md missing token: {token}"

    dev_doc_text = _read(dev_doc)
    for token in (
        "verify_cad_backend_profile_scope.sh",
        "bash -n scripts/verify_cad_backend_profile_scope.sh",
        "shell syntax stays valid",
        "LOGIN_USERNAME",
        "Claude Code CLI was used in non-interactive `-p` mode",
    ):
        assert token in dev_doc_text, f"dev-and-verification doc missing token: {token}"

    delivery_doc_index_text = _read(delivery_doc_index)
    assert (
        "docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md"
        in delivery_doc_index_text
    ), "DELIVERY_DOC_INDEX missing CAD backend profile scope verifier doc"


def test_cad_backend_profile_scope_verifier_restores_scope_on_mid_run_failure(
    tmp_path,
) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_cad_backend_profile_scope.sh"

    server = _VerifierFailureServer(("127.0.0.1", 0), _VerifierFailureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = os.environ.copy()
        env.update(
            {
                "BASE_URL": f"http://127.0.0.1:{server.server_port}",
                "TOKEN": "test-token",
                "OUTPUT_DIR": str(tmp_path),
                "RUN_TENANT_SCOPE": "0",
            }
        )
        cp = subprocess.run(  # noqa: S603,S607
            ["bash", str(script)],
            text=True,
            capture_output=True,
            env=env,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert cp.returncode != 0, cp.stdout + "\n" + cp.stderr
    combined = (cp.stdout or "") + "\n" + (cp.stderr or "")
    assert "[trap] restored org scope" in combined
    assert server.state["capabilities_calls"] == 1
    assert server.state["deletes"] == ["org"]
    assert server.state["puts"], "Expected override PUT before failure"
    assert server.state["effective"] == server.state["initial"]["effective"]
    assert server.state["source"] == server.state["initial"]["source"]


def test_cad_backend_profile_scope_verifier_restores_scope_when_put_returns_error(
    tmp_path,
) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_cad_backend_profile_scope.sh"

    server = _VerifierFailureServer(("127.0.0.1", 0), _VerifierFailureHandler)
    server.state["fail_put_after_apply"] = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = os.environ.copy()
        env.update(
            {
                "BASE_URL": f"http://127.0.0.1:{server.server_port}",
                "TOKEN": "test-token",
                "OUTPUT_DIR": str(tmp_path),
                "RUN_TENANT_SCOPE": "0",
            }
        )
        cp = subprocess.run(  # noqa: S603,S607
            ["bash", str(script)],
            text=True,
            capture_output=True,
            env=env,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert cp.returncode != 0, cp.stdout + "\n" + cp.stderr
    combined = (cp.stdout or "") + "\n" + (cp.stderr or "")
    assert "[trap] restored org scope" in combined
    assert server.state["puts"], "Expected override PUT before failure"
    assert server.state["deletes"] == ["org"]
    assert server.state["effective"] == server.state["initial"]["effective"]
    assert server.state["source"] == server.state["initial"]["source"]
