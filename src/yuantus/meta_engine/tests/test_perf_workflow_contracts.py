from __future__ import annotations

import json
import re
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".github").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .github/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_perf_workflows_reference_existing_gate_profiles_and_helpers() -> None:
    repo_root = _find_repo_root(Path(__file__))

    cfg_path = repo_root / "configs" / "perf_gate.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    profiles = cfg.get("profiles", {})
    assert isinstance(profiles, dict)

    p5_wf = repo_root / ".github" / "workflows" / "perf-p5-reports.yml"
    roadmap_wf = repo_root / ".github" / "workflows" / "perf-roadmap-9-3.yml"

    p5_text = _read(p5_wf)
    roadmap_text = _read(roadmap_wf)

    # Gate config contract: workflows must reference config + a known profile.
    assert "--config configs/perf_gate.json" in p5_text
    assert re.search(r"--profile\s+p5_reports\b", p5_text)
    assert "p5_reports" in profiles

    assert "--config configs/perf_gate.json" in roadmap_text
    assert re.search(r"--profile\s+roadmap_9_3\b", roadmap_text)
    assert "roadmap_9_3" in profiles

    # Baseline download contract: workflows must use the shared helper script.
    assert "scripts/perf_ci_download_baselines.sh" in p5_text
    assert re.search(r"--workflow\s+perf-p5-reports\.yml\b", p5_text)

    assert "scripts/perf_ci_download_baselines.sh" in roadmap_text
    assert re.search(r"--workflow\s+perf-roadmap-9-3\.yml\b", roadmap_text)

