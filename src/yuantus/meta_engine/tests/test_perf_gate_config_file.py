from __future__ import annotations

import json
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "configs").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + configs/)")


def test_perf_gate_config_file_is_valid_and_has_required_profiles() -> None:
    repo_root = _find_repo_root(Path(__file__))
    cfg_path = repo_root / "configs" / "perf_gate.json"
    assert cfg_path.is_file(), f"Missing perf gate config: {cfg_path}"

    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data.get("version") == 1

    defaults = data.get("defaults")
    assert isinstance(defaults, dict)
    assert int(defaults.get("window")) >= 1
    assert str(defaults.get("baseline_stat")) in {"max", "median"}
    assert float(defaults.get("pct")) >= 0.0
    assert float(defaults.get("abs_ms")) >= 0.0

    # The CI workflows reference these profiles.
    profiles = data.get("profiles")
    assert isinstance(profiles, dict)
    for name in ("p5_reports", "roadmap_9_3"):
        prof = profiles.get(name)
        assert isinstance(prof, dict), f"Missing profile '{name}'"
        baseline_glob = str(prof.get("baseline_glob") or "").strip()
        assert baseline_glob, f"profiles.{name}.baseline_glob must be non-empty"
        assert ".md" in baseline_glob, f"profiles.{name}.baseline_glob should match markdown reports"

    db_overrides = data.get("db_overrides", {})
    assert isinstance(db_overrides, dict)
    pg = db_overrides.get("postgres", {})
    if pg:
        assert isinstance(pg, dict)
        assert float(pg.get("pct")) >= 0.0
        assert float(pg.get("abs_ms")) >= 0.0

