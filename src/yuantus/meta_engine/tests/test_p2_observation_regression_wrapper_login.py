from __future__ import annotations

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _ObservationHandler(BaseHTTPRequestHandler):
    login_requests: list[dict] = []
    observed_paths: list[str] = []
    auth_headers: list[str] = []
    tenant_headers: list[str | None] = []
    org_headers: list[str | None] = []

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _write_json(self, payload: object, *, code: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record_auth(self) -> None:
        self.__class__.observed_paths.append(self.path)
        self.__class__.auth_headers.append(self.headers.get("Authorization", ""))
        self.__class__.tenant_headers.append(self.headers.get("x-tenant-id"))
        self.__class__.org_headers.append(self.headers.get("x-org-id"))

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/v1/auth/login":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self.__class__.login_requests.append(payload)
            self._write_json({"access_token": "test-token"})
            return
        self.send_error(404)

    def do_GET(self) -> None:  # noqa: N802
        self._record_auth()
        if self.headers.get("Authorization") != "Bearer test-token":
            self._write_json({"detail": "unauthorized"}, code=401)
            return

        if self.path.startswith("/api/v1/eco/approvals/dashboard/summary"):
            self._write_json(
                {
                    "pending_count": 1,
                    "overdue_count": 1,
                    "escalated_count": 0,
                    "by_stage": [],
                    "by_role": [],
                    "by_assignee": [],
                }
            )
            return
        if self.path.startswith("/api/v1/eco/approvals/dashboard/items"):
            self._write_json(
                [
                    {"eco_id": "eco-pending", "is_overdue": False, "is_escalated": False},
                    {"eco_id": "eco-overdue", "is_overdue": True, "is_escalated": False},
                ]
            )
            return
        if self.path.startswith("/api/v1/eco/approvals/dashboard/export?fmt=json"):
            self._write_json(
                [
                    {"eco_id": "eco-pending", "is_overdue": False, "is_escalated": False},
                    {"eco_id": "eco-overdue", "is_overdue": True, "is_escalated": False},
                ]
            )
            return
        if self.path.startswith("/api/v1/eco/approvals/dashboard/export?fmt=csv"):
            body = (
                "eco_id,eco_name,eco_state,stage_id,stage_name,approval_id,assignee_id,"
                "assignee_username,approval_type,required_role,is_overdue,is_escalated,"
                "approval_deadline,hours_overdue\r\n"
                "eco-pending,,,,,,,,,,False,False,,\r\n"
                "eco-overdue,,,,,,,,,,True,False,,\r\n"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/v1/eco/approvals/audit/anomalies":
            self._write_json(
                {
                    "no_candidates": [],
                    "escalated_unresolved": [],
                    "overdue_not_escalated": [{"eco_id": "eco-overdue"}],
                    "total_anomalies": 1,
                }
            )
            return

        self.send_error(404)


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def test_p2_observation_regression_wrapper_supports_login_flow(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_observation_regression.sh"
    assert script.is_file(), f"Missing script: {script}"

    _ObservationHandler.login_requests = []
    _ObservationHandler.observed_paths = []
    _ObservationHandler.auth_headers = []
    _ObservationHandler.tenant_headers = []
    _ObservationHandler.org_headers = []

    server = ThreadingHTTPServer(("127.0.0.1", 0), _ObservationHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    output_dir = tmp_path / "result"
    env = {
        "BASE_URL": f"http://127.0.0.1:{server.server_port}",
        "TENANT_ID": "tenant-1",
        "ORG_ID": "org-1",
        "USERNAME": "admin",
        "PASSWORD": "admin-secret",
        "OUTPUT_DIR": str(output_dir),
        "OPERATOR": "pytest",
        "ENVIRONMENT": "test",
        "EVAL_MODE": "current-only",
        "PY": "python3",
    }

    try:
        cp = subprocess.run(  # noqa: S603,S607
            ["bash", str(script)],
            text=True,
            capture_output=True,
            cwd=repo_root,
            env={**env},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert (output_dir / "OBSERVATION_RESULT.md").is_file()
    assert (output_dir / "OBSERVATION_EVAL.md").is_file()
    assert "- verdict: PASS" in (output_dir / "OBSERVATION_EVAL.md").read_text(encoding="utf-8")

    assert _ObservationHandler.login_requests == [
        {
            "tenant_id": "tenant-1",
            "org_id": "org-1",
            "username": "admin",
            "password": "admin-secret",
        }
    ]
    assert _ObservationHandler.observed_paths == [
        "/api/v1/eco/approvals/dashboard/summary",
        "/api/v1/eco/approvals/dashboard/items",
        "/api/v1/eco/approvals/dashboard/export?fmt=json",
        "/api/v1/eco/approvals/dashboard/export?fmt=csv",
        "/api/v1/eco/approvals/audit/anomalies",
    ]
    assert set(_ObservationHandler.auth_headers) == {"Bearer test-token"}
    assert set(_ObservationHandler.tenant_headers) == {"tenant-1"}
    assert set(_ObservationHandler.org_headers) == {"org-1"}

