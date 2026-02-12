from __future__ import annotations

from pathlib import Path


EXPECTED_HEADINGS = [
    "## Core",
    "## Ops & Deployment",
    "## Product/UI Integration",
    "## Verification Reports (Latest)",
    "## Development & Verification",
    "## Optional",
    "## External (Not Included in Package)",
]


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "docs").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + docs/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_delivery_doc_index_major_h2_headings_are_stable_and_ordered() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()

    headings = [line.strip() for line in _read(index_path).splitlines() if line.startswith("## ")]
    major = [h for h in headings if h in EXPECTED_HEADINGS]

    assert major == EXPECTED_HEADINGS, (
        "docs/DELIVERY_DOC_INDEX.md major H2 headings changed or reordered.\n"
        "Expected:\n"
        + "\n".join(f"- {h}" for h in EXPECTED_HEADINGS)
        + "\nCurrent:\n"
        + "\n".join(f"- {h}" for h in major)
    )

