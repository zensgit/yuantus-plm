from __future__ import annotations

import os
import sys
from pathlib import Path


def shell_test_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["PYTHON"] = sys.executable
    return env
